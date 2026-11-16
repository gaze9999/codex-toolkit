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
結果含 `missing_in_target`、`extra_in_target`、`changed` 與每一邊的讀取錯誤

| `status` | 條件 | 結束碼 |
| --- | --- | --- |
| `match` | 至少比對到一個檔案且完全一致 | 0 |
| `different` | 有缺少、多出、內容不同或讀取錯誤 | 1 |
| `empty` | 兩邊都沒有檔案被比對, 通常是 `--include` 沒有符合的項目 | 1 |

`--include`、`--exclude` 與 `--read-root` 可重複, 其餘選項重複指定時回報錯誤

## 輸出

每次執行在標準輸出印出數行摘要, 最後是報告檔的路徑, 完整結果只寫入報告檔, 結果再多摘要長度也不變

| 選項 | 內容 |
| --- | --- |
| 省略 `--format` | 只寫入 `report.md` |
| `--format json,md,html` | 寫入指定的格式, 以逗號分隔, `md` 可寫成 `markdown`, `all` 代表三種 |
| `--out DIR` | 報告資料夾, 必須尚未存在且位於受檢查的目錄之外, 省略時使用系統暫存目錄下的新資料夾 |

HTML 與 Markdown 由共用的 [report-html](../report-html/README.md) 產生, `--style-dir` 可套用外觀套件, 輸入錯誤的結束碼為 2

## Stdio MCP

```sh
workspace-inspection mcp --read-root /path/to/workspace --read-root /path/to/another
```

每個 `--read-root` 是一個已授權的絕對路徑目錄, 工具只接受這些目錄以內的絕對路徑

| 工具 | 參數 | 結果 |
| --- | --- | --- |
| `workspace_status` | 無 | 伺服器版本、讀取根目錄與 `read_only` |
| `validation_evidence` | `root`, 選用 `limit`、`current` | 摘要、每次執行一列 (`run`、`started`、結果筆數、`validity`)、最多 40 筆未通過或已失效的結果 (`attention`)、無法讀取的執行 |
| `compare_environment` | `source`、`target`, 選用 `includes`、`excludes`、`use_default_excludes`、`max_files` | 摘要、`status`、各類筆數, 以及每個清單的前 40 筆 |

兩個查詢工具的文字內容是摘要與報告路徑, `reports` 欄位指向寫入系統暫存目錄的 `report.md` 與 `report.json`, 完整結果在 `report.json`, 格式與 `--format json` 相同

工具名稱與參數沿用 Python 版, 查詢結果改為上述的精簡形式, `workspace_status.versions` 回報本工具的版本

MCP 保持受檢查的專案目錄唯讀, 產生報告的工具會在暫存目錄寫入新檔案, 因此標示 `readOnlyHint: false`、`destructiveHint: false` 與 `idempotentHint: false`
