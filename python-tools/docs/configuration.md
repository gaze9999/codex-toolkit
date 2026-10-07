# 設定與備援機制

## 設計原則

輸入與輸出路徑不放在 `.env`, 每次執行由位置參數或 `--root`, `--output`, `--target-file` 等 CLI 選項提供, 未指定時只使用文件中明載的目前目錄或來源同目錄預設

這可避免工具被單一專案, 使用者目錄或同步磁碟路徑綁定, 也讓同一份 working copy 可直接處理不同專案

## `.env` 支援欄位

`setup/.env` 為選用檔案

```powershell
Copy-Item .\setup\.env.example .\setup\.env
```

| 變數 | 使用工具 | 預設值 | 無效時行為 |
| --- | --- | --- | --- |
| `TOOL_HISTORY_NAMESPACE` | `markdown.guarded_markdown_update` | `project-task` | 顯示警告後改用 `project-task` |
| `TOOL_FIELD_MATRIX_TITLE` | `documents.extract_field_matrix` | 依來源檔名產生 | 空值時使用來源檔名 |
| `TOOL_TOKENIZER_ENCODING` | `text.tokenizer` | `cl100k_base` | tiktoken 無法使用時改採字元比率估算 |
| `TOOL_TOKENIZER_ASCII_CHARS_PER_TOKEN` | `text.tokenizer` | `4` | 非有限值或小於等於 0 時顯示警告並改用 `4` |
| `TOOL_TOKENIZER_NONASCII_CHARS_PER_TOKEN` | `text.tokenizer` | `2` | 非有限值或小於等於 0 時顯示警告並改用 `2` |

不需要 `.env` 時可直接刪除或忽略, CLI-only 操作仍可執行

## 優先序

1. CLI 選項, 例如 `--title`, `--encoding`, `--namespace`
2. process environment 中的 `TOOL_*` 變數
3. `--env-file` 指定檔案或 `setup/.env`
4. 工具內建安全預設值

路徑沒有 `.env` 優先序, 一律由 CLI 決定

## 容錯規則

`shared/config.py` 讀取設定檔失敗時採用可繼續執行的容錯方式

- 預設 `.env` 不存在時安靜使用內建預設
- 明確指定的 `--env-file` 不存在或無法讀取時顯示警告, 仍繼續使用 process environment 與內建預設
- 無效行, 非 `TOOL_*` key, 重複 key, 未閉合引號, 找不到的 `${TOOL_NAME}` 或循環引用會被忽略並顯示警告
- process environment 會覆蓋 `.env` 的同名值
- CLI 明確傳入的錯誤值通常回傳結束代碼 `2`, 不會自行改成另一個路徑或檔案

## 自訂設定檔

支援設定變數的工具可用 `--env-file`

```powershell
python launch-cli.py text.tokenizer --env-file .\profile.env --text "example"
python launch-cli.py documents.extract_field_matrix converted.md --env-file .\profile.env
python launch-cli.py markdown.guarded_markdown_update --env-file .\profile.env --target-file history.md inspect history
```

`.env` 支援 UTF-8 BOM, 空白行, `#` 開頭註解, 以單引號或雙引號包住的完整值, 以及 `${TOOL_OTHER_KEY}` 變數引用, 不支援 shell command substitution 或行尾註解

## 新增 CLI 工具

在 `src/<用途>/` 新增模組, 提供 `main()` 與 `if __name__ == "__main__"` 入口, CLI 會自動發現, 輔助模組沒有此入口就不會列為工具

```python
"""整理輸入檔案的內容"""

def main():
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
```

例如 `src/reports/summarize.py` 可使用 `python launch-cli.py reports.summarize`, 自動代號為 `reports-summarize`, 分類依第一層用途資料夾

需要固定別名、中文名稱或用途說明時, 在 `src/shared/tool_catalog.py` 的 `_OVERRIDES` 加入 `ToolSpec`, 同一份清單用於原始碼及免安裝 CLI, 新工具加入後需重新發布才會進入已封裝成品

工具應自行解析參數、檢查相依套件並提供 `--help`, 新增相關測試與用途文件, 不自動安裝相依套件或啟動背景服務
