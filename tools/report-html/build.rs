//! Chooses the built-in styles: src/default.css, or an appearance package named by
//! REPORT_HTML_STYLE_DIR at build time. The package is checked like a runtime --style-dir.
#[allow(dead_code)]
#[path = "src/package.rs"]
mod package;

use std::{env, fs, path::PathBuf};

fn main() {
    println!("cargo:rerun-if-env-changed=REPORT_HTML_STYLE_DIR");
    println!("cargo:rerun-if-changed=src/default.css");
    println!("cargo:rerun-if-changed=src/package.rs");
    let out = PathBuf::from(env::var_os("OUT_DIR").expect("OUT_DIR"));
    let (css, label) = match env::var_os("REPORT_HTML_STYLE_DIR").filter(|dir| !dir.is_empty()) {
        Some(dir) => {
            let dir = PathBuf::from(dir);
            println!("cargo:rerun-if-changed={}", dir.display());
            let package = package::load(&dir)
                .unwrap_or_else(|error| panic!("REPORT_HTML_STYLE_DIR: {error}"));
            (
                package.css,
                format!(
                    "外觀套件 {} (建置時內嵌, SHA-256 {})",
                    package.version,
                    &package.sha256[..12]
                ),
            )
        }
        None => {
            // The built-in styles carry their own revision: the first 12 hex digits of the file's SHA-256.
            let css = fs::read_to_string("src/default.css").expect("src/default.css");
            let label = format!("內建樣式 (SHA-256 {})", &package::sha256(&css)[..12]);
            (css, label)
        }
    };
    fs::write(out.join("style.css"), css).expect("write style.css");
    fs::write(out.join("style-label.txt"), label).expect("write style-label.txt");
}
