use super::*;
use std::fs::{File, Metadata, OpenOptions};
#[cfg(windows)]
use std::os::windows::{
    fs::{MetadataExt, OpenOptionsExt},
    io::AsRawHandle,
};
#[cfg(windows)]
use windows_sys::Win32::Storage::FileSystem::*;
pub fn link(m: &Metadata) -> bool {
    #[cfg(windows)]
    {
        m.file_attributes() & FILE_ATTRIBUTE_REPARSE_POINT != 0
    }
    #[cfg(not(windows))]
    {
        m.file_type().is_symlink()
    }
}
pub fn plain(p: &Path) -> Result<()> {
    if !p.is_absolute()
        || p.components()
            .any(|c| matches!(c, std::path::Component::ParentDir))
    {
        return Err("Unsafe path".into());
    }
    for part in p.ancestors() {
        if link(&fs::symlink_metadata(part)?) {
            return Err("Linked path".into());
        }
    }
    Ok(())
}
#[cfg(windows)]
fn open(p: &Path, delete: bool) -> Result<File> {
    let mut opt = OpenOptions::new();
    opt.access_mode(FILE_READ_ATTRIBUTES | if delete { 0x10000 } else { 0 })
        .share_mode(if delete { 0 } else { 7 })
        .custom_flags(FILE_FLAG_OPEN_REPARSE_POINT | FILE_FLAG_BACKUP_SEMANTICS);
    Ok(opt.open(p)?)
}
fn identity(f: &File) -> Result<String> {
    #[cfg(windows)]
    {
        let mut info: BY_HANDLE_FILE_INFORMATION = unsafe { std::mem::zeroed() };
        if unsafe { GetFileInformationByHandle(f.as_raw_handle() as _, &mut info) } == 0 {
            return Err(io::Error::last_os_error().into());
        }
        if info.nFileIndexHigh == 0 && info.nFileIndexLow == 0 {
            return Err("Missing file identity".into());
        }
        Ok(format!(
            "{}:{}:{}",
            info.dwVolumeSerialNumber, info.nFileIndexHigh, info.nFileIndexLow
        ))
    }
    #[cfg(unix)]
    {
        use std::os::unix::fs::MetadataExt;
        let m = f.metadata()?;
        Ok(format!("{}:{}", m.dev(), m.ino()))
    }
}
pub(crate) fn stamp(f: &File) -> Result<Value> {
    let m = f.metadata()?;
    if link(&m) {
        return Err("Linked object".into());
    }
    Ok(
        json!({"identity":identity(f)?,"size":m.len(),"modified_ns":m.modified()?.duration_since(UNIX_EPOCH)?.as_nanos().to_string(),"directory":m.is_dir()}),
    )
}
pub fn snapshot(p: &Path) -> Result<Value> {
    plain(p)?;
    #[cfg(windows)]
    let f = open(p, false)?;
    #[cfg(unix)]
    let f = {
        use std::os::unix::fs::OpenOptionsExt;
        OpenOptions::new()
            .read(true)
            .custom_flags(libc::O_NOFOLLOW | libc::O_NONBLOCK)
            .open(p)?
    };
    stamp(&f)
}
pub fn remove(p: &Path, expected: &Value, stage: &Path) -> Result<()> {
    plain(p)?;
    #[cfg(windows)]
    {
        // Pin every parent against rename or replacement until disposition is committed.
        let mut guards = Vec::new();
        for dir in p.ancestors().skip(1).collect::<Vec<_>>().into_iter().rev() {
            let guard = OpenOptions::new()
                .access_mode(FILE_READ_ATTRIBUTES)
                .share_mode(FILE_SHARE_READ | FILE_SHARE_WRITE)
                .custom_flags(FILE_FLAG_BACKUP_SEMANTICS | FILE_FLAG_OPEN_REPARSE_POINT)
                .open(dir)?;
            if link(&guard.metadata()?) {
                return Err("Linked parent".into());
            }
            guards.push(guard)
        }
        let file = open(p, true)?;
        let actual = stamp(&file)?;
        verify(&actual, expected)?;
        let disposition = FILE_DISPOSITION_INFO { DeleteFile: 1 };
        if unsafe {
            SetFileInformationByHandle(
                file.as_raw_handle() as _,
                FileDispositionInfo,
                &disposition as *const _ as _,
                std::mem::size_of_val(&disposition) as u32,
            )
        } == 0
        {
            return Err(io::Error::last_os_error().into());
        }
        drop(file);
    }
    #[cfg(target_os = "macos")]
    return crate::darwin::remove(p, expected, stage);
    #[cfg(not(any(target_os = "macos", windows)))]
    return Err("Unsupported platform".into());
    #[cfg(windows)]
    let _ = stage;
    #[allow(unreachable_code)]
    Ok(())
}
pub(crate) fn verify(current: &Value, expected: &Value) -> Result<()> {
    if current["identity"] != expected["identity"]
        || (current["directory"] != true && current != expected)
    {
        return Err("Identity or metadata changed".into());
    }
    Ok(())
}
