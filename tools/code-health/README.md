# Code Health 程式碼健檢

選定本機程式碼根目錄, 找出孤兒檔案、未使用的匯出或類別成員、重複片段, 並列出函式的分支與行數, Rust 函式庫、CLI 與 stdio MCP 共用同一份分析核心

使用目的平台的 Rust 1.89 以上版本建置, 建置完成後, 可直接執行產生的 `code-health`, 掃描在本機唯讀執行, 無需 Node 套件、編譯器、網路或專案指令稿

```sh
cargo build --locked --release --manifest-path tools/code-health/Cargo.toml
code-health scan --root /path/to/project --entry src/main.ts --format markdown
code-health scan --root /path/to/project --checks unused,duplicates --min-tokens 40
code-health mcp --allow-root /path/to/project
```

`scan` 預設輸出 JSON, 加上 `--format markdown` 可輸出表格, 重複使用 `--entry` 可指定多個相對於掃描根目錄的進入點, 工具也採用掃描範圍內可解析的 `tsconfig*.json` `files` 與 `project.json` 的 `main` 或 `browser`

`--marker-pattern` 接受呼叫端提供的 Rust 正規表示式, 符合時保留整個檔案, `--retain-file` 指定相對路徑, `--retain-range path:START:END` 指定已核對的行號範圍, 包含起訖行, 保留的檔案仍參與模組圖, 其中的匯入會計入使用端

| 檢查 | 證據 |
| --- | --- |
| `unused` | JS/TS 靜態匯入、重新匯出、barrel、相對路徑與支援的 TypeScript 路徑別名, 同檔使用、類別成員與對應的 Angular 範本引用 |
| `duplicates` | JS/TS、HTML 與樣式的重複 token 片段, 合併相鄰片段並按檔案配對彙總, 忽略註解與字面值內容, JS/TS 可辨識一致改名的識別字 |
| `complexity` | JS/TS 可辨識的函式、方法與箭頭函式, 列出行號範圍及分支數, 包含邏輯運算子與三元運算, 巢狀函式分開計數 |

動態匯入、計算出的路徑、裝飾器或反射引用、缺少進入點及無法解析的設定列入 `needs_review`, 提出移除前先核對框架註冊、繼承、外部用戶端、產生檔及範圍外引用
工具略過相依套件目錄、建置輸出及符號連結, 大小、讀取或結果上限影響涵蓋範圍時回報 `partial`, 可縮小掃描根目錄或檢查範圍
需要精確的 ESLint 指標時, 使用專案既有的規則與門檻

## Stdio MCP

登錄已建置的執行檔, 參數使用 `mcp --allow-root /path/to/project`, 每個 `--allow-root` 對應一個已授權的本機根目錄

唯一的唯讀工具 `code_health` 接受允許範圍內的絕對 `root`, 以及選用的 `entries`、`checks`、`marker_patterns`、`retained_files`、`retained_ranges` (`path`、`start_line`、`end_line`) 與 `min_tokens` (8 至 1000, 預設 50), 結果與 CLI 的 JSON 相同, 參數或根目錄錯誤會回傳 MCP 工具錯誤, CLI 則以狀態碼 2 結束
