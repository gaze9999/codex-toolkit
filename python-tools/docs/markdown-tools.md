# Markdown 工具

## Markdown 結構差異

兩份 Markdown 的標題、清單項目與表格列比較已改由 Toolkit 的 Rust 工具 `markdown-checks diff` 提供, 見[工具說明](../../tools/markdown-checks/README.md)

## `markdown/guarded_markdown_update.py`

以明確目標檔, SHA-256 樂觀鎖定, dry-run, 原子取代與寫入後讀回檢查, 保護單一 Markdown 更新

全域選項必須放在子命令前

```powershell
python launch-cli.py markdown.guarded_markdown_update --target-file progress.md inspect progress
python launch-cli.py markdown.guarded_markdown_update --target-file progress.md inspect progress --section "## Current"
python launch-cli.py markdown.guarded_markdown_update --target-file progress.md replace progress --content replacement.md --expect CURRENT_SHA --section "## Current"
python launch-cli.py markdown.guarded_markdown_update --target-file history.md append history --content entry.md --expect CURRENT_SHA --entry-id task-001
```

### `inspect`

- 目標別名可為 `context`, `progress`, `history`, 別名只描述用途, 實際路徑由 `--target-file` 決定
- 未指定 `--section` 時輸出 SHA-256 與標題清單
- 指定 `--section` 時要求標題完全相符且只出現一次
- `--out` 只可搭配 `--section`, 並以排他建立模式匯出至新檔, 不覆寫既有檔案

### `replace`

- 目標別名只允許 `context` 或 `progress`
- 取代內容必須以完全相同的標題開頭, 且不能包含同層或更高層的其他章節
- `--expect` 必須等於 inspect 取得的目前 SHA-256
- 預設只回報 `dry-run`, `--write` 才寫入

### `append`

- 目標別名只允許 `history`
- `--entry-id` 必須唯一, 相同內容已存在時回傳 `unchanged`, 不同內容使用相同 ID 時拒絕
- 標記命名空間優先使用 `--namespace`, 再使用 `TOOL_HISTORY_NAMESPACE`, 無效時顯示警告並改用 `project-task`

預設寫入會在同一目錄使用暫存檔, 原子取代與逐位元組讀回檢查, 同步磁碟 placeholder 無法原子取代時, 可明確加上 `--in-place`, 工具會先建立備份, 受保護地寫入後再讀回核對, 成功才刪除備份, 失敗時保留備份路徑

結束代碼 `0` 表示檢查, 無變更, dry-run 或已驗證寫入完成, `2` 表示 SHA 已過期, 標題或項目規格不符, 路徑或 I/O 錯誤

## `markdown.validate_structure`

```powershell
python launch-cli.py markdown.validate_structure document.md
```

唯讀檢查 ATX 標題跳號, fenced code block, 行尾空白與選用版本, 兩空白 hard break 合法, 缺少版本僅 INFO, 無標題與行尾空白僅 WARN. 這是有限結構檢查, 不是完整 Markdown parser, 不強加風格, CLI 使用 English / ASCII, 來源非 ASCII 字元以 escape 顯示

結束代碼 0 為無結構錯誤 (可含 WARN), 1 為層級或 fence 錯誤, 2 為參數或 UTF-8 檔案無法讀取. API `my_py_document_core.validation.analyze(text)` 回傳 checks, failures, warnings

此 module 為 standalone Skill validator 單一維護來源, 不手改 generated snapshot. 使用 `python launch-cli.py scripts.export_markdown_validator --output <snapshot-file>` 產生含套件版本及 source SHA-256 的 snapshot, `--check` 僅比對. Snapshot 只用標準函式庫, 無 repo 或 core 安裝相依
