//! Output layer shared with other tools through report-html.
pub use report_html::output::{column, emit, parse_formats, Emit, Rendered, DEFAULT_FORMATS};
use std::path::{Path, PathBuf};

/// The common report-html fields for one check, collected from the checked root and the system.
pub fn page_meta(root: &Path, scope: Option<&str>, inputs: &[PathBuf]) -> serde_json::Value {
    report_html::meta::collect(&report_html::meta::Facts {
        tool: "angular-checks",
        version: env!("CARGO_PKG_VERSION"),
        format: report_html::SCHEMA,
        target: Some(root),
        scope,
        inputs,
        ..Default::default()
    })["meta"]
        .clone()
}
