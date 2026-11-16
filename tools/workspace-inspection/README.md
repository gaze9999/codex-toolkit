# Workspace Inspection 工作區檢查

唯讀的目錄比對與驗證證據查詢, Rust 函式庫、CLI 與 stdio MCP 共用同一份核心, 取代原本的 Python 版 workspace core 與 MCP 伺服器

使用 Rust 1.89 以上的 stable 版本建置, 建置時需要同一份儲存庫內的 `tools/report-html`, 執行時無需 Python、Node 套件或網路

```sh
cargo build --locked --release --manifest-path tools/workspace-inspection/Cargo.toml
workspace-inspection evidence --root /path/to/validation-runs --current-baseline baseline.json
workspace-inspection compare --source /path/a --target /path/b --exclude "*.log"
workspace-inspection compare --source /path/a --target /path/b --format all --out /path/outside/report
workspace-inspection mcp --read-root /path/to/workspace
```

## 驗證證據 `evidence`

彙整 `--root` 底下 `run-*/results.json` 的既有結果, 依資料夾名稱由新到舊, 只讀取檔案, 不重新執行任何指令

| 選項 | 內容 |
| --- | --- |
| `--root DIR` | 執行資料夾的上層, 預設為目前資料夾 |
| `--limit N` | 最多讀取的執行數, 1 至 1000, 預設 20 |
| `--current-baseline FILE` | 目前來源與產物的出處 JSON, 提供時每次執行與每筆結果多一個 `validity` 判定 |

`results.json` 需要是物件, `results` 為物件陣列, 每筆保留 `name`、`status`、`reason`、`command`、`log`、`source`、`baseline`, 無法讀取的執行列在 `errors`, 此時結束碼為 1

出處 JSON 與已記錄的 `baseline` 使用相同欄位, 全部選填:

| 欄位 | 格式 |
| --- | --- |
| `source_revision` | 7 至 64 個十六進位字元 |
| `source_diff_sha256`、`artifact_sha256` | 64 個十六進位字元 |
| `source_files` | 路徑對應 SHA-256 的物件 |
| `affected_paths` (目前)、`covered_paths` (已記錄) | 路徑字串陣列 |

`validity.status` 的判定只依據提供的出處, 不讀取來源檔案:

| 狀態 | 條件 |
| --- | --- |
| `outdated` | 檔案雜湊、產物雜湊不同, 或沒有檔案雜湊可比時 revision 或 diff 雜湊不同 |
| `unverified` | 沒有任何一致的來源識別, 或已記錄的 baseline 缺少、格式錯誤 |
| `partial` | 來源一致, 但缺少雜湊、涵蓋範圍未知, 或受影響路徑有未涵蓋的項目 |
| `current` | 來源一致且受影響路徑都在已記錄的涵蓋範圍內 |

`reasons` 列出每項判定依據, `uncovered_paths` 列出未涵蓋的路徑

## 環境比對 `compare`

以相對路徑、大小與 SHA-256 比對兩個彼此獨立、互不包含的目錄, 兩邊都只讀取

| 選項 | 內容 |
| --- | --- |
| `--source DIR`、`--target DIR` | 必要 |
| `--include GLOB`、`--exclude GLOB` | 可重複, 比對完整相對路徑或檔名, `*` 可跨越 `/`, 支援 `?` 與 `[...]`、`[!...]` |
| `--no-default-excludes` | 停用預設排除 |
| `--max-files N` | 每一邊的檔案上限, 1 至 200000, 預設 20000 |

預設排除版本控制資料、虛擬環境、`__pycache__`、`.pyc`、`.env*`、`*.key`、`*.pem`、`credentials*`、`secrets*`, 符號連結一律略過, 略過的數量記在 `excluded`
結果含 `missing_in_target`、`extra_in_target`、`changed` 與每一邊的讀取錯誤, 完全一致時 `status` 為 `match` 且結束碼為 0, 有差異時為 1

## 輸出

`evidence` 與 `compare` 預設將 JSON 印到標準輸出, `--format` 可用 `json`、`md`、`html`, 以逗號分隔, `all` 代表三種
包含 `html`、多種格式或指定 `--out` 時寫入新資料夾的 `report.json`、`report.md`、`report.html`, 資料夾必須位於受檢查的目錄之外, 省略 `--out` 時放在系統暫存目錄
HTML 與 Markdown 由共用的 [report-html](../report-html/README.md) 產生, `--style-dir` 可套用外觀套件, 輸入錯誤的結束碼為 2

## Stdio MCP

```sh
workspace-inspection mcp --read-root /path/to/workspace --read-root /path/to/another
```

每個 `--read-root` 是一個已授權的絕對路徑目錄, 工具只接受這些目錄以內的絕對路徑

| 工具 | 參數 | 結果 |
| --- | --- | --- |
| `workspace_status` | 無 | 伺服器版本、讀取根目錄與 `read_only` |
| `validation_evidence` | `root`, 選用 `limit`、`current` | 與 `evidence` 的 JSON 相同 |
| `compare_environment` | `source`、`target`, 選用 `includes`、`excludes`、`use_default_excludes`、`max_files` | 與 `compare` 的 JSON 相同 |

工具名稱、參數與結果欄位沿用 Python 版, `workspace_status.versions` 改為回報本工具的版本
