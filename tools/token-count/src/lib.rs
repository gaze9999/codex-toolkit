//! Offline exact BPE token counting compatible with tiktoken encodings.

pub mod context;
pub mod html;

use serde_json::{json, Value};
use std::path::{Component, Path, PathBuf};
use tiktoken_rs::CoreBPE;

pub const DEFAULT_ENCODING: &str = "o200k_base";
pub const ENCODINGS: [&str; 7] = [
    "gpt2",
    "r50k_base",
    "p50k_base",
    "p50k_edit",
    "cl100k_base",
    "o200k_base",
    "o200k_harmony",
];

/// Vocabularies are compiled into the binary, so lookup never touches the network.
pub fn encoding(name: &str) -> Result<&'static CoreBPE, String> {
    use tiktoken_rs::*;
    Ok(match name {
        "o200k_base" => o200k_base_singleton(),
        "o200k_harmony" => o200k_harmony_singleton(),
        "cl100k_base" => cl100k_base_singleton(),
        "p50k_base" => p50k_base_singleton(),
        "p50k_edit" => p50k_edit_singleton(),
        // gpt2 and r50k_base share the same ranks and split pattern.
        "r50k_base" | "gpt2" => r50k_base_singleton(),
        _ => {
            return Err(format!(
                "未知的編碼: {name}, 可用: {}",
                ENCODINGS.join(", ")
            ))
        }
    })
}

/// Literal text count: special-token-looking strings are ordinary text.
pub fn count_text(text: &str, encoding_name: &str) -> Result<usize, String> {
    Ok(encoding(encoding_name)?.encode_ordinary(text).len())
}

/// One source result in the documented field order.
pub fn count_result(source: &str, text: &str, encoding_name: &str) -> Result<Value, String> {
    let tokens = count_text(text, encoding_name)?;
    let chars = text.chars().count();
    let ratio = if tokens == 0 {
        Value::Null
    } else {
        json!(chars as f64 / tokens as f64)
    };
    Ok(json!({
        "source": source,
        "encoding": encoding_name,
        "method": "tiktoken",
        "chars": chars,
        "tokens": tokens,
        "utf8_bytes": text.len(),
        "chars_per_token": ratio,
    }))
}

/// Decode UTF-8 and drop one leading BOM, preserving CRLF and all whitespace.
pub fn decode_utf8_sig(bytes: Vec<u8>, source: &Path) -> Result<String, String> {
    let bytes = match bytes.strip_prefix(b"\xEF\xBB\xBF") {
        Some(rest) => rest.to_vec(),
        None => bytes,
    };
    String::from_utf8(bytes).map_err(|error| {
        format!(
            "{} 不是有效的 UTF-8 文字 (位元組 {})",
            source.display(),
            error.utf8_error().valid_up_to()
        )
    })
}

pub fn read_utf8_sig(path: &Path) -> Result<String, String> {
    let bytes =
        std::fs::read(path).map_err(|error| format!("無法讀取 {}: {error}", path.display()))?;
    decode_utf8_sig(bytes, path)
}

/// Integer with thousands separators, like Python's `{:,}`.
pub fn grouped(value: u64) -> String {
    let digits = value.to_string();
    let mut out = String::with_capacity(digits.len() + digits.len() / 3);
    for (index, digit) in digits.chars().enumerate() {
        if index > 0 && (digits.len() - index).is_multiple_of(3) {
            out.push(',');
        }
        out.push(digit);
    }
    out
}

pub fn total_tokens(results: &[Value]) -> u64 {
    results
        .iter()
        .filter_map(|row| row["tokens"].as_u64())
        .sum()
}

pub fn format_report(results: &[Value]) -> String {
    let mut lines = Vec::new();
    for result in results {
        let as_u64 = |key: &str| result[key].as_u64().unwrap_or(0);
        lines.push(format!("來源: {}", result["source"].as_str().unwrap_or("")));
        lines.push(format!(
            "編碼: {}",
            result["encoding"].as_str().unwrap_or("")
        ));
        lines.push(format!("字元數: {}", grouped(as_u64("chars"))));
        lines.push(format!("Token 數: {}", grouped(as_u64("tokens"))));
        lines.push(format!("UTF-8 bytes: {}", grouped(as_u64("utf8_bytes"))));
        lines.push(match result["chars_per_token"].as_f64() {
            Some(ratio) => format!("字元/Token: {ratio:.2}"),
            None => "字元/Token: 無 (空文字)".to_string(),
        });
        lines.push(String::new());
    }
    if results.len() > 1 {
        lines.push(format!(
            "Token 總數 (各來源分別計算後加總): {}",
            grouped(total_tokens(results))
        ));
    }
    format!("{}\n", lines.join("\n").trim_end())
}

pub fn format_json(results: Vec<Value>) -> String {
    let total = total_tokens(&results);
    let report = json!({"results": results, "total_tokens": total});
    format!(
        "{}\n",
        serde_json::to_string_pretty(&report).unwrap_or_default()
    )
}

/// Absolute path with symlinks resolved for the existing prefix, like `Path.resolve()`.
pub fn resolve(path: &Path) -> PathBuf {
    let absolute = if path.is_absolute() {
        path.to_path_buf()
    } else {
        std::env::current_dir().unwrap_or_default().join(path)
    };
    let mut normal = PathBuf::new();
    for part in absolute.components() {
        match part {
            Component::CurDir => {}
            Component::ParentDir => {
                let resolved = std::fs::canonicalize(&normal).unwrap_or(normal.clone());
                normal = resolved.parent().map(Path::to_path_buf).unwrap_or(resolved);
            }
            other => normal.push(other),
        }
    }
    let mut existing = normal.clone();
    let mut rest = Vec::new();
    loop {
        if let Ok(real) = std::fs::canonicalize(&existing) {
            let mut out = real;
            out.extend(rest.iter().rev());
            return out;
        }
        match (existing.parent(), existing.file_name()) {
            (Some(parent), Some(name)) => {
                rest.push(name.to_os_string());
                existing = parent.to_path_buf();
            }
            _ => return normal,
        }
    }
}

/// Comparison key matching `os.path.normcase(str(path.resolve()))`.
pub fn path_key(path: &Path) -> String {
    let text = resolve(path).to_string_lossy().into_owned();
    if cfg!(windows) {
        text.replace('/', "\\").to_lowercase()
    } else {
        text
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn groups_thousands() {
        assert_eq!(grouped(0), "0");
        assert_eq!(grouped(999), "999");
        assert_eq!(grouped(1000), "1,000");
        assert_eq!(grouped(1234567), "1,234,567");
    }

    #[test]
    fn counts_literal_special_tokens() {
        assert_eq!(count_text("hello world", "o200k_base").unwrap(), 2);
        assert!(count_text("<|endoftext|>", "cl100k_base").unwrap() > 1);
        assert_eq!(count_text("", "o200k_base").unwrap(), 0);
        assert!(encoding("missing").is_err());
    }

    #[test]
    fn strips_only_one_bom() {
        let text =
            decode_utf8_sig(b"\xEF\xBB\xBF\xEF\xBB\xBFa\r\n".to_vec(), Path::new("x")).unwrap();
        assert_eq!(text, "\u{feff}a\r\n");
        assert!(decode_utf8_sig(vec![0xff], Path::new("x")).is_err());
    }
}
