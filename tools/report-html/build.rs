//! Chooses the built-in styles: the static package in src/style, or an appearance package named by
//! REPORT_HTML_STYLE_DIR at build time. Both are checked like a runtime --style-dir.
#[allow(dead_code)]
#[path = "src/package.rs"]
mod package;

use std::{env, fs, path::PathBuf};

fn main() {
    println!("cargo:rerun-if-env-changed=REPORT_HTML_STYLE_DIR");
    println!("cargo:rerun-if-changed=src/style");
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
            // The built-in styles are a static package: its version and the first 12 hex digits of the styles' SHA-256 identify them.
            let package = package::load(std::path::Path::new("src/style"))
                .unwrap_or_else(|error| panic!("src/style: {error}"));
            let label = format!(
                "內建樣式 {} (SHA-256 {})",
                package.version,
                &package.sha256[..12]
            );
            (package.css, label)
        }
    };
    fs::write(out.join("style.css"), css).expect("write style.css");
    fs::write(out.join("style-label.txt"), label).expect("write style-label.txt");
}
