# Token Count Token 計數

在本機精確計算 BPE Token, 輸出彩色 Token 檢視 HTML, 並依 Global,Project Agent,Skills 與工具設定預估 Codex Context, 輸出格式與 [Python Tools](../../python-tools/docs/text-validation-tools.md) 的 `token-count`,`context-budget` 相同

編碼字典隨執行檔內建 (由 [tiktoken-rs](https://crates.io/crates/tiktoken-rs) 提供), 首次使用不必下載, 不需要 Python,API key 或網路, 輸入文字不會離開本機

## 建置

使用 Rust 1.89 以上版本, Setup 以 `cargo install --locked --path <Toolkit>/tools/token-count` 安裝, 也可在 Toolkit 根目錄手動執行同一指令

## 指令

```sh
token-count --text "要計算的文字"
token-count --input prompt.md --output tokens.json
token-count --input a.txt b.md --json
token-count --text "繁體中文與 emoji 👩‍💻" --html tokens.html
cat prompt.md | token-count --encoding cl100k_base
token-count context --project /path/project
token-count context --project /path/project --active-skill /path/SKILL.md --tool-schema tools.json --output budget.json
```

| 模式 | 用途 |
| --- | --- |
| 計數 (預設) | 逐檔計算字元數,Token 數,UTF-8 bytes 與字元/Token, 多個來源分別計算後加總 |
| `context` | 分類列出 Global/Project Agent,Skills 探索清單,啟用的 Skills/角色,Memory,工具定義與社群系統基礎的 Token 預估 |

可用編碼: `o200k_base` (預設),`o200k_harmony`,`cl100k_base`,`p50k_base`,`p50k_edit`,`r50k_base`,`gpt2`

## 計數選項

| 選項 | 內容 |
| --- | --- |
| `--input FILE [FILE ...]` | 一個或多個 UTF-8 文字檔, 與 `--text` 擇一使用, 兩者都未提供時讀取 UTF-8 stdin |
| `--text TEXT` | 直接提供要計算的文字 |
| `--encoding NAME` | 選擇編碼 |
| `--json` | 輸出 `results` 陣列與 `total_tokens` |
| `--output NEW_FILE` | 另存結果, `.json` 副檔名自動使用 JSON |
| `--html NEW.html` | 另存離線彩色 Token 檢視, 點選 Token 可查看 ID 與 UTF-8 位元組 |
| `--max-display-tokens N` | 每個來源在 HTML 中的彩色顯示上限, 預設 2000, 完整計數不受影響 |

UTF-8 BOM 不列入文字, 保留 CRLF,空白與最後換行, `chars` 是 Unicode code point 數量, `<|endoftext|>` 等字串視為一般文字計算, 空文字為 0 Token, `chars_per_token` 為 `null`

## Context 選項

| 選項 | 內容 |
| --- | --- |
| `--project DIR` | 專案目錄, 預設目前資料夾, 從 Git 根目錄往下每層取一份指示檔 |
| `--codex-home DIR` | Codex 設定目錄, 預設 `CODEX_HOME` 或使用者的 `.codex` |
| `--instruction`、`--active-skill`、`--active-role`、`--content FILE` | 加入明確引用的指示,啟用的 Skill/角色本文與任務文字, 可重複 |
| `--skill-root DIR` | 加入 Skill 探索根目錄, 可重複 |
| `--tool-schema FILE` | 提供工具定義文字, 取代逐項工具估算, 可重複 |
| `--builtin-tools N`、`--mcp-tools N` | 未提供工具定義時的內建工具 (預設 10) 與 MCP 工具情境數量 |
| `--profile FILE` | 改用指定的預估設定, 預設使用內建的 [context_estimates.json](../../python-tools/src/text/context_estimates.json), 與 Python 版共用同一份 |
| `--json`、`--output NEW_FILE` | JSON 輸出與另存結果 |

預估方法與來源日期見 [環境預估](../../skills/token-count/references/context-budget.md)

## 結束碼與輸出

成功回傳 `0`, 參數錯誤,編碼不存在,來源不是 UTF-8 或匯出失敗時回傳 `2`, 不產生結果, 已存在的輸出檔一律拒絕覆寫, 輸出目錄需先存在

## 驗證

```sh
cargo test --locked --manifest-path tools/token-count/Cargo.toml
cargo clippy --locked --manifest-path tools/token-count/Cargo.toml --all-targets -- -D warnings
cargo fmt --manifest-path tools/token-count/Cargo.toml --check
```
