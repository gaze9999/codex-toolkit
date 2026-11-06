use super::*;
use std::ffi::CString;
use std::fs::File;
use std::os::fd::{AsRawFd, FromRawFd};
use std::os::unix::ffi::OsStrExt;

// Capture the entry exclusively, then verify its identity in a private directory
// before unlinking. A concurrent replacement is restored without overwriting.
pub fn remove(path: &Path, expected: &Value, stage: &Path) -> Result<()> {
    let check = std::process::Command::new("/usr/sbin/lsof")
        .arg("-t")
        .arg("--")
        .arg(path)
        .output()?;
    if check.status.code() != Some(1) || !check.stderr.is_empty() || !check.stdout.is_empty() {
        return Err("Active use or unavailable lsof check".into());
    }
    let mut parent = File::open("/")?;
    for part in path.parent().ok_or("Missing parent")?.components() {
        if let std::path::Component::Normal(n) = part {
            parent = open_dir(&parent, &CString::new(n.as_bytes())?)?
        }
    }
    let name = CString::new(path.file_name().ok_or("Missing name")?.as_bytes())?;
    let staging = CString::new(stage.file_name().ok_or("Missing staging name")?.as_bytes())?;
    let slot = c"entry";
    let parent_fd = parent.as_raw_fd();
    if unsafe { libc::mkdirat(parent_fd, staging.as_ptr(), 0o700) } != 0 {
        return Err(io::Error::last_os_error().into());
    }
    let guard = open_dir(&parent, &staging)?;
    let fd = guard.as_raw_fd();
    let capture = unsafe {
        libc::renameatx_np(
            parent_fd,
            name.as_ptr(),
            fd,
            slot.as_ptr(),
            libc::RENAME_EXCL,
        )
    };
    let result = (|| -> Result<()> {
        if capture != 0 {
            return Err(io::Error::last_os_error().into());
        }
        let entry_fd = unsafe {
            libc::openat(
                fd,
                slot.as_ptr(),
                libc::O_RDONLY | libc::O_NOFOLLOW | libc::O_NONBLOCK | libc::O_CLOEXEC,
            )
        };
        if entry_fd < 0 {
            return Err(io::Error::last_os_error().into());
        }
        let entry = unsafe { File::from_raw_fd(entry_fd) };
        let actual = safety::stamp(&entry)?;
        safety::verify(&actual, expected)?;
        let flags = if expected["directory"] == true {
            libc::AT_REMOVEDIR
        } else {
            0
        };
        if unsafe { libc::unlinkat(fd, slot.as_ptr(), flags) } != 0 {
            return Err(io::Error::last_os_error().into());
        }
        Ok(())
    })();
    if result.is_err()
        && capture == 0
        && unsafe {
            libc::renameatx_np(
                fd,
                slot.as_ptr(),
                parent_fd,
                name.as_ptr(),
                libc::RENAME_EXCL,
            )
        } != 0
    {
        return Err(format!(
            "Restore conflict, retained {}",
            stage.join("entry").display()
        )
        .into());
    }
    if unsafe { libc::unlinkat(parent_fd, staging.as_ptr(), libc::AT_REMOVEDIR) } != 0 {
        return Err(format!("Inspect staging directory {}", stage.display()).into());
    }
    result
}
fn open_dir(parent: &File, name: &std::ffi::CStr) -> Result<File> {
    let fd = unsafe {
        libc::openat(
            parent.as_raw_fd(),
            name.as_ptr(),
            libc::O_RDONLY | libc::O_DIRECTORY | libc::O_NOFOLLOW | libc::O_CLOEXEC,
        )
    };
    if fd < 0 {
        return Err(io::Error::last_os_error().into());
    }
    Ok(unsafe { File::from_raw_fd(fd) })
}
