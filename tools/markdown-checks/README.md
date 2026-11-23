# Markdown Checks Markdown 檢查

Markdown 的唯讀結構檢查、變更檔案的文件影響分類, 以及以 SHA-256 保護的單一同步目標寫入, 共用同一個執行檔

## 建置

使用 Rust 1.89 以上版本, Setup 以 `cargo install --locked --path <Toolkit>/tools/markdown-checks` 安裝, 也可在 Toolkit 根目錄手動執行同一指令, 執行時只有 `scan-changes` 讀 Git 需要 Git

## 指令

```sh
markdown-checks diff --left before.md --right after.md
markdown-checks context-brief brief.md --required-heading Scope --json
markdown-checks scan-changes --repo /path/repository --json
markdown-checks scan-changes --repo /path/repository --table --max-files 0
markdown-checks sync-inspect notes.md --json
markdown-checks sync-write notes.md --content-file new.md --expected-sha256 <sync-inspect 的 sha256>
```

| 指令 | 用途 | 結束碼 |
| --- | --- | --- |
| `diff --left FILE --right FILE` | 比較兩份 Markdown 在 fenced code 以外的 ATX 標題、清單項目與表格列, 輸出各自 SHA-256 與 `only_left`、`only_right`、`order_changed` | 0 完成, 2 輸入不存在或無法讀取, 有差異仍是 0 |
| `context-brief FILE` | context brief 的語言中立結構檢查: 標題階層、code fence 是否關閉、必要標題、來源位置標記與常見憑證樣式 | 1 有檢查不通過, `--strict` 把警告視為不通過 |
| `scan-changes` | 依路徑把已暫存、未暫存與未追蹤的變更分類為文件影響 `yes`、`maybe`、`no`, 沒有工作樹變更時改看最後一個 commit | 0 完成, 2 Git 或輸入錯誤 |
| `sync-inspect FILE` | 讀取一個 Markdown 同步目標的路徑、SHA-256、位元組數與標題, 不寫入 | 0 完成, 2 不是 Markdown 或不存在 |
| `sync-write FILE` | 目標的 SHA-256 仍等於 `--expected-sha256` 時, 以 UTF-8 內容整檔取代, 保留目標原本的檔案權限 | 3 目標已被改動, 2 輸入錯誤 |

## 選項

| 選項 | 適用 | 內容 |
| --- | --- | --- |
| `--required-heading TEXT` | `context-brief` | 必須有包含這段文字的標題, 比對不分大小寫, 可重複 |
| `--json`、`--strict` | `context-brief` | JSON 輸出, 警告視為不通過 |
| `--repo DIR` | `scan-changes` | 儲存庫根目錄, 預設目前資料夾 |
| `--base REF` | `scan-changes` | 改為比較此 ref 與目前工作樹 |
| `--diff-file FILE` | `scan-changes` | 改為讀取 unified diff, 不呼叫 Git |
| `--max-files N` | `scan-changes` | 明細最多列出的檔案數, 預設 80, 0 為全部 |
| `--stat` | `scan-changes` | 每個檔案加上 `stage`、`added`、`deleted`, 可搭配 `--json` |
| `--table` | `scan-changes` | 輸出含階段與增減行數的 Markdown 表格, 欄位為 File、Stage、Change、Added、Deleted、Category、Doc impact, 與 `--json` 擇一使用 |
| `--include-notion-metadata` | `sync-inspect` | 只在明確授權的 Notion 同步流程使用, 另列 Notion 網址、頁面 ID 與 `sync_mode` |
| `--content-file FILE`、`--expected-sha256 HASH`、`--dry-run` | `sync-write` | 取代內容、讀取時的雜湊與只驗證不寫入 |

## 階段與增減行數

`--stat` 與 `--table` 的數字取自 `git diff --numstat`, 由工具直接讀取, 可直接貼進變更報告作為檔案清單

| `stage` | 來源 |
| --- | --- |
| `staged`、`unstaged`、`staged+unstaged` | 已暫存、未暫存, 或兩者都有, 兩者都有時增減行數為兩段相加 |
| `untracked` | 未追蹤且未忽略的檔案, `added` 為檔案行數, `deleted` 為 0 |
| `commit` | 沒有工作樹變更時的最後一個 commit |
| `base` | 指定 `--base` 時與該 ref 的差異 |
| `diff` | 指定 `--diff-file` 時, 行數欄為空值 |

二進位檔的 `added` 與 `deleted` 在 JSON 為 `null`, 表格顯示 `-`, 未追蹤檔案在 4 MiB 以內才計算行數, 重新命名的檔案以新路徑列出
這些欄位描述檔案層級的事實, 變更的原因、影響與驗收由報告撰寫者補充

`diff`、`sync-inspect` 與 `scan-changes` 不修改任何檔案, `sync-write` 先在目標旁建立暫存檔再以重新命名取代, 失敗時移除暫存檔

## 驗證

```sh
cargo test --locked --manifest-path tools/markdown-checks/Cargo.toml
cargo clippy --locked --manifest-path tools/markdown-checks/Cargo.toml --all-targets -- -D warnings
```
