# Report HTML 共用報告頁面

把一份 JSON 報告資料轉成單檔離線 HTML, 供本儲存庫的掃描與檢查工具共用, Rust 函式庫與 CLI 使用同一份產生器

頁面含基本資訊、統計卡片、筆數分布條、分頁表格與關鍵字搜尋, 跟隨系統深淺色, 樣式與指令稿都內嵌在檔案內, 開啟時無需網路
使用 Rust 1.89 以上的 stable 版本建置, 相依套件為 `serde_json` 與 `sha2`

```sh
cargo build --locked --release --manifest-path tools/report-html/Cargo.toml
report-html render --input report-data.json --out /path/to/report.html
some-tool --json | report-html render --input - > report.html
report-html render --input report-data.json --style-dir /path/to/appearance-package
```

`--input -` 從標準輸入讀取, 省略 `--out` 時頁面印到標準輸出, `--out` 指定的檔案已存在時回報錯誤並保留原檔, 參數或資料錯誤以狀態碼 2 結束

## 報告資料

```json
{
  "schema": "report-html/1",
  "title": "Code health 報告",
  "tags": [{ "label": "涵蓋範圍完整", "tone": "success" }],
  "info": [["掃描根目錄", "/path/to/project"], ["掃描檔案數", 42]],
  "note": "以下都是靜態分析的候選",
  "stats": [{ "label": "未使用", "value": 6, "tone": "warning", "bar": true }],
  "sections": [
    {
      "label": "未使用",
      "empty": "沒有候選",
      "columns": [
        { "key": "path", "label": "檔案", "kind": "code" },
        { "key": "line", "label": "行", "kind": "number" },
        { "key": "evidence", "label": "證據" }
      ],
      "rows": [{ "path": "src/a.ts", "line": 4, "evidence": "No importing consumer in scope" }]
    }
  ]
}
```

| 欄位 | 必要 | 內容 |
| --- | --- | --- |
| `schema` | 是 | 固定為 `report-html/1` |
| `title` | 是 | 頁面標題 |
| `lang` | | 頁面語言, 預設 `zh-Hant-TW` |
| `tags` | | 基本資訊上方的標籤, `tone` 可用 `neutral`、`category`、`success`、`warning`、`error` |
| `info` | | `[名稱, 值]` 的列表, 樣式來源會自動附在最後一列 |
| `note` | | 統計卡片上方的說明文字 |
| `stats` | | 統計卡片, `value` 可為數字或文字, `bar` 為 `true` 且 `value` 是正整數時計入分布條 |
| `sections` | | 每個項目是一個分頁, `columns` 的 `kind` 可用 `text` (預設)、`number`、`code`, `rows` 以 `key` 取值, `empty` 是沒有資料時的文字, `note` 顯示在表格上方 |
| `headings` | | 覆寫固定文字: `info`、`stats`、`sections`、`search`、`placeholder`、`style`、`distribution` |

資料內的所有文字都會跳脫後再放進頁面

## 樣式

預設使用內建樣式 [default.css](src/default.css), `--style-dir` 指向外觀套件資料夾時改用套件的樣式
頁面標記採用 Workbench UI 靜態版的 class 與 `--wb-*` 變數名稱, 可直接套用其靜態樣式包, 版面補充樣式使用 `rh-` 前綴

外觀套件是一個資料夾, 內含 `manifest.json` 與它指定的樣式檔, 載入時逐項核對:

| `manifest.json` 欄位 | 條件 |
| --- | --- |
| `format` | `static` |
| `entry.styles` | 同資料夾內的樣式檔名, 檔案上限 2 MiB |
| `classes` | 涵蓋頁面用到的每個 class (`REQUIRED_CLASSES`), 以 `-` 結尾的項目視為前綴, 缺少時回報缺了哪些 |
| `assets.<樣式檔名>.sha256` | 與樣式檔內容的 SHA-256 相同 |
| `version` | 顯示在報告的樣式列 |

### 建置時內嵌

建置時設定 `REPORT_HTML_STYLE_DIR` 指向外觀套件, 該套件會通過相同的核對後編進執行檔, 成為預設樣式, 報告的樣式列顯示版本、"建置時內嵌" 與 SHA-256 前 12 碼, `--style-dir` 仍可在執行時覆寫

```sh
REPORT_HTML_STYLE_DIR=/path/to/appearance-package CARGO_TARGET_DIR=/path/outside/this/checkout \
  cargo build --locked --release --manifest-path tools/report-html/Cargo.toml
```

以 path 相依套件使用本函式庫的工具 (例如 code-health) 在同樣的環境變數下建置, 也會內嵌同一份樣式
內嵌後的執行檔與建置輸出含有套件的樣式內容, 依該套件的授權決定能否散布, 建置輸出請用 `CARGO_TARGET_DIR` 放在本儲存庫之外
未設定環境變數時, 執行檔只含本儲存庫的內建樣式

## 函式庫

```toml
report-html = { path = "../report-html" }
```

```rust
let page = report_html::render(&data, &report_html::Style::builtin())?;
```

| 函式 | 用途 |
| --- | --- |
| `render(&data, &style)` | 產生 HTML 頁面 |
| `markdown(&data)` | 由同一份報告資料產生 Markdown: 標題、基本資訊、統計與各分頁的表格 |
| `Style::builtin()`、`Style::load(dir)` | 內建樣式 (或建置時內嵌的套件) 與執行時載入的外觀套件 |
| `new_folder(out, scanned, prefix)` | 建立新的報告資料夾, 省略路徑時放在系統暫存目錄, 並確保位於受掃描的根目錄之外 |
| `escape(text)` | 與頁面相同的跳脫規則 |
| `output::emit(...)`、`output::parse_formats(...)` | CLI 共用的輸出層: 單一文字格式印到標準輸出, 其餘寫入新資料夾的 `report.*` 並印出摘要 |

使用範例見 [code-health 的轉換](../code-health/src/html.rs) 、[angular-checks](../angular-checks/src/main.rs) 與 [workspace-inspection](../workspace-inspection/src/main.rs)
