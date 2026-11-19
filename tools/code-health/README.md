# Code Health 程式碼健檢

選定本機程式碼根目錄, 找出孤兒檔案、未使用的匯出或類別成員、重複片段, 並列出函式的分支與行數, Rust 函式庫、CLI 與 stdio MCP 共用同一份分析核心

使用目的平台的 Rust 1.89 以上版本建置, 建置時需要同一份儲存庫內的 `tools/report-html`, 建置完成後, 可直接執行產生的 `code-health`, 掃描在本機唯讀執行, 無需 Node 套件、編譯器、網路或專案指令稿

```sh
cargo build --locked --release --manifest-path tools/code-health/Cargo.toml
code-health scan --root /path/to/project --entry src/main.ts --format markdown
code-health scan --root /path/to/project --checks unused,duplicates --min-tokens 40
code-health scan --root /path/to/project --format all --out /path/outside/project/report
code-health scan --root /path/to/project --evidence /path/to/evidence.json --format all
code-health mcp --allow-root /path/to/project
```

`--entry`、`--marker-pattern`、`--retain-file`、`--retain-range` 可重複, 其餘選項重複指定時回報錯誤

每次執行在標準輸出印出數行摘要, 最後是報告檔的路徑, 完整結果只寫入報告檔, 結果再多摘要長度也不變

| 選項 | 內容 |
| --- | --- |
| 省略 `--format` | 只寫入 `report.md` |
| `--format json,md,html` | 寫入指定的格式, 以逗號分隔, `md` 可寫成 `markdown`, `all` 代表三種 |
| `--out DIR` | 報告資料夾, 必須尚未存在且位於受檢查的目錄之外, 省略時使用系統暫存目錄下的新資料夾 |

```text
code-health: 400 files, coverage partial
unused 1500 (export 1100, member 400); most in src/feat/f0.ts (11), src/feat/f1.ts (11), src/feat/f2.ts (11)
duplicates 1500 regions in 320 file pairs
complexity: 1500 functions; most branches 14 in src/feat/f3.ts calc3_0 (9 lines)
needs_review 2
report: /tmp/code-health-1794822129-73967/report.md
```

需要逐筆資料時指定 `--format json` 後讀取 `report.json`, 並以 `--checks` 或較小的 `--root` 縮小範圍

`report.html` 是單檔離線頁面, 由共用的 [report-html](../report-html/README.md) 產生, 含結果筆數、分頁明細與關鍵字搜尋, 跟隨系統深淺色, 預設使用內建樣式
`--style-dir` 指向外觀套件資料夾時改用套件的樣式: 資料夾需有 `manifest.json` (`format` 為 `static`, `entry.styles` 為同資料夾內的樣式檔名) 與該樣式檔, 頁面標記採用 Workbench UI 靜態版的 class 與 `--wb-*` 變數名稱, 可直接套用其靜態樣式包

重複使用 `--entry` 可指定多個相對於掃描根目錄的進入點, 工具也採用掃描範圍內可解析的 `tsconfig*.json` `files` 與 `project.json` 的 `main` 或 `browser`

`--marker-pattern` 接受呼叫端提供的 Rust 正規表示式, 符合時保留整個檔案, `--retain-file` 指定相對路徑, `--retain-range path:START:END` 指定已核對的行號範圍, 包含起訖行, 保留的檔案仍參與模組圖, 其中的匯入會計入使用端

| 檢查 | 證據 |
| --- | --- |
| `unused` | JS/TS 靜態匯入、重新匯出、barrel、相對路徑與支援的 TypeScript 路徑別名, 同檔使用、類別成員與對應的 Angular 範本引用 |
| `duplicates` | JS/TS、HTML 與樣式的重複 token 片段, 合併相鄰片段並按檔案配對彙總, 忽略註解與字面值內容, JS/TS 可辨識一致改名的識別字 |
| `complexity` | JS/TS 可辨識的函式、方法與箭頭函式, 列出行號範圍及分支數, 包含邏輯運算子與三元運算, 巢狀函式分開計數 |

動態匯入、計算出的路徑、裝飾器或反射引用、缺少進入點及無法解析的設定列入 `needs_review`, 提出移除前先核對框架註冊、繼承、外部用戶端、產生檔及範圍外引用
工具略過相依套件目錄、建置輸出及符號連結, 大小、讀取或結果上限影響涵蓋範圍時回報 `partial`, 可縮小掃描根目錄或檢查範圍
需要精確的 ESLint 指標時, 使用專案既有的規則與門檻

## 候選 ID 與語意佐證

`unused` 與 `needs_review` 的每一筆都有 `id`, 由種類、路徑與符號組成, 同檔其他位置的修改不會改變它, 相同鍵值重複時加上 `~2` 這類序號

| 種類 | 格式 | 範例 |
| --- | --- | --- |
| 檔案 | `file:<路徑>` | `file:src/orphan.ts` |
| 匯出 | `export:<路徑>#<名稱>` | `export:src/lib.ts#spare` |
| 類別成員 | `member:<路徑>#<類別>.<名稱>` | `member:src/a.component.ts#AComponent.save` |
| 需人工確認 | `review:<路徑>#<符號>`, 沒有符號時為 `review:<路徑>@<行>`, 針對整次掃描的說明為 `review:scan` | `review:src/b.ts#handler` |

匯出與類別成員的候選另有 `line` 與 `column`, 指向宣告名稱的位置, 行與欄都從 1 開始, 欄以 UTF-16 單位計算, 可直接作為語言伺服器查詢參照的位置

掃描本身維持語法層級, 語言伺服器或審查者依 `id` 核對後, 可用佐證檔把結果合併回報告:

```json
{
  "schema": "code-health-evidence/v1",
  "root": "/path/to/project",
  "items": [
    { "id": "export:src/lib.ts#spare", "status": "confirmed", "provider": "typescript-language-server",
      "provider_version": "4.3.3", "coverage": "project", "references": 0 },
    { "id": "export:src/lib.ts#viaDecorator", "status": "refuted", "references": 1,
      "locations": [{ "path": "src/app.module.ts", "line": 12 }], "note": "由 DI 註冊使用" }
  ]
}
```

| 欄位 | 內容 |
| --- | --- |
| `status` | `confirmed` (查無使用端, 候選成立)、`refuted` (找到使用端)、`unsupported`、`timeout`、`error` |
| `provider`、`provider_version`、`coverage` | 實際回答的後端、版本與查詢範圍, 選填 |
| `references`、`locations`、`note` | 使用端數量、最多 50 個位置與補充說明, 選填 |
| `root` | 選填, 提供時必須與掃描根目錄相同 |

合併後每筆候選多一個 `semantic` 物件, 報告多一個 `semantic` 摘要: 各狀態筆數、沒有佐證的 `unchecked` 筆數, 以及找不到對應候選的 `unmatched` ID (通常代表佐證來自另一次掃描或程式碼已變更)
佐證只附加在候選旁, 候選清單與其他檢查結果維持原樣, Markdown 與 HTML 在有佐證時多一欄語意確認
未使用檢查的完整 JSON 報告包含 `source_files`, 記錄實際讀取的來源與已解析專案設定檔的 SHA-256
`code-health-evidence/v2` 須提供 `root` 與該份 `source_files`, 已確認或反駁的項目也需提供 `position` 的 `path`、`line` 與 `column`
舊名稱 `code-health-evidence/1` 與 `code-health-evidence/2` 仍可讀取, 規則分別與 `/v1`、`/v2` 相同
重新掃描發現來源或候選位置不同時拒絕合併
`semantic.freshness` 的 `matched_scan_sources` 表示同批掃描來源相符, 部分掃描或未配對候選回報 `partial`, 舊版佐證維持 `unverified`
來源相符後仍須核對語言伺服器的涵蓋範圍、動態引用與外部使用端
CLI 使用 `--evidence FILE`, 上限 16 MiB 與 5000 筆, MCP 單一訊息上限 8 MiB, 足以容納 5000 筆佐證, 超過時回傳錯誤並繼續服務

## Stdio MCP

登錄已建置的執行檔, 參數使用 `mcp --allow-root /path/to/project`, 每個 `--allow-root` 對應一個已授權的本機根目錄

工具 `code_health` 只讀取專案, 接受允許範圍內的絕對 `root`, 以及選用的 `entries`、`checks`、`marker_patterns`、`retained_files`、`retained_ranges` (`path`、`start_line`、`end_line`)、`min_tokens` (8 至 1000, 預設 50) 與 `evidence` (內嵌的佐證物件, 格式同上)

回傳內容是精簡的, 完整結果寫入系統暫存目錄的新資料夾:

| 欄位 | 內容 |
| --- | --- |
| 文字內容 | 與 CLI 相同的摘要與報告路徑 |
| `summary`、`reports` | 摘要各行, 以及 `report.md` 與 `report.json` 的路徑 |
| `counts`、`files_scanned`、`partial` | 各類筆數與涵蓋狀態 |
| `candidates`、`candidates_omitted` | 前 40 筆未使用候選 (`id`、`kind`、`path`、`line`、`column`、`name`、`semantic`) 與未列出的筆數 |
| `review`、`review_omitted` | 前 40 筆帶有符號位置的待確認項目與其餘筆數 |
| `semantic` | 有佐證時的彙總 |

要看其他候選時以 `checks` 或較小的 `root` 縮小範圍, 參數或根目錄錯誤會回傳 MCP 工具錯誤, CLI 則以狀態碼 2 結束

MCP 保持受檢查的專案目錄唯讀, 產生報告的工具會在暫存目錄寫入新檔案, 因此標示 `readOnlyHint: false`、`destructiveHint: false` 與 `idempotentHint: false`
