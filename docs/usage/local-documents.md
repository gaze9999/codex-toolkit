# Local Documents MCP 操作教學

`local_documents` 用於本機文件擷取, OCR 備援與 Markdown 安全更新, 不需要遠端 API Key, 先依 [安裝說明](../setup/cli.md) 註冊, 再由支援 MCP 的 client 呼叫工具

MCP 實作位於 `codex-setup/mcp_servers/local_documents/`, CLI 核心使用已安裝的 `my-py-document-core` versioned API, 不需另一個 repo 的路徑, 日常操作不需要手動啟動 server, client 會管理 stdio 程序

## 先確認可用範圍

可以對 Codex 說:

```text
請呼叫 local_documents 的 document_status, 告訴我目前是否可用, 支援哪些格式, 可以讀寫哪些資料夾
```

Tool: `document_status`

```json
{}
```

`status=ready` 表示相依套件與隨附 OCR 模型存在, 不是所有文件版面都已驗證, `read_roots` 與 `write_roots` 是目前設定的範圍, 未設定 write root 時不能寫入

下面的 `C:\path\...` 都是示意路徑, 請換成已允許的真實絕對路徑, macOS/Linux 使用該電腦的絕對路徑, 例如 `/absolute/documents/spec.pdf`

## 擷取文件, 先不寫檔

可以對 Codex 說:

```text
使用 local_documents 擷取 C:\path\documents\spec.pdf, OCR 使用 auto, 先回傳內容與來源 SHA-256, 不寫入檔案; 如有部分結果或截斷, 請一併說明
```

Tool: `extract_document`

```json
{
  "source": "C:\\path\\documents\\spec.pdf",
  "ocr": "auto",
  "write_output": false,
  "max_chars": 30000
}
```

| 回傳欄位 | 如何判讀 |
| --- | --- |
| `source_sha256` | 來源內容的 SHA-256, 用於辨識本次擷取版本 |
| `content` | 原生擷取本文與選用的 OCR 補充 |
| `written` | 是否實際寫入 output, 預覽時為 false |
| `status=partial` | OCR 有失敗或省略, 請查看 `ocr.errors` 與 `ocr.omitted_items` |
| `truncated=true` | 回傳本文已截斷, `content_chars` 是完整本文字數 |
| `output_sha256` | 完整 Markdown 的 hash, 預覽時計算預定輸出, 寫入後可用它核對檔案 |

支援 PDF, XLSX, DOCX, PPTX, CSV, TXT 與 PNG/JPEG/TIFF/BMP/WebP 等點陣圖, 來源上限 128 MiB, 原始文件仍是規格權威, OCR 信心分數不能證明欄位或表格關係正確

## 需要 OCR 時

| `ocr` | 行為 |
| --- | --- |
| `off` | 只使用原生擷取, 點陣圖來源不能使用此模式 |
| `auto` | 補 PDF 沒有原生文字的頁面及 Office 文件內嵌點陣圖 |
| `force` | 對 PDF 的選定頁面執行 OCR, 適合文字與圖片混合頁, 結果可能與原生文字重複 |

Tool: `extract_document`

```json
{
  "source": "C:\\path\\documents\\spec.pdf",
  "ocr": "force",
  "pages": [2, 3],
  "ocr_max_items": 2,
  "write_output": false
}
```

`pages` 從 1 起算, 只控制 PDF OCR 的頁碼, 原生擷取仍涵蓋整份文件, 不可將此參數當作整份文件的頁面篩選, Office 文件或圖片不使用 `pages`

OCR 預設最多 10 頁或圖片, 可設 1-100, 模型在本機 CPU 執行, 不上傳來源文件, 工具呼叫時不下載模型, 回傳記錄包含位置, 每行文字, 信心分數與方框, 超出上限會回報省略

## 明確寫出完整 Markdown

先檢查擷取結果, 再明確要求寫入新檔:

Tool: `extract_document`

```json
{
  "source": "C:\\path\\documents\\spec.pdf",
  "output": "C:\\path\\output\\spec-extracted.md",
  "ocr": "auto",
  "write_output": true
}
```

output 必須位於 write root, 父資料夾已存在, 副檔名為 `.md`, 新 output 不要提供 `expected_output_sha256`; `written=true` 才表示完成寫入, 回傳文字即使被截斷, output 仍保存完整產生內容

要取代既有 output 時, 先使用 `inspect_markdown` 讀取該檔目前的 `sha256`, 再將它放進 `extract_document.expected_output_sha256`, 不使用來源 hash 或上次預覽新產生的 hash, 內容已改變時會拒絕覆寫, 必須重新檢視再決定

新檔使用排他 hard link 原子發布, 檔案系統不支援時回報錯誤, 不自動降級成直接覆寫

## 定位既有 Markdown 抽出版

Tool: `locate_markdown_extracts`

```json
{
  "source": "C:\\path\\documents\\spec.pdf",
  "search_roots": ["C:\\path\\documents", "C:\\path\\markdown"]
}
```

工具會依來源路徑與來源 SHA-256 尋找候選, `current` 表示 metadata hash 與目前來源一致, `stale` 表示路徑相符但來源內容已改變, 也可只提供已知的 `source_sha256`, 此工具唯讀, 不會自行決定應採用哪一份或更新檔案

## 檢查 Markdown 章節

Tool: `inspect_markdown`

```json
{
  "target": "C:\\path\\documents\\guide.md",
  "heading": "## 使用方式"
}
```

不提供 `heading` 時回傳 SHA-256 與標題清單, 提供時讀取完全相符且唯一的章節, 包含標題本身, 重複標題會拒絕選取, fenced code block 內的標題不算章節

## 安全更新單一章節

1. 呼叫 `inspect_markdown`, 檢視內容並取得目前 `sha256`
2. 使用相同 SHA-256 呼叫 `update_markdown`, 先設 `write=false` 預覽
3. 確認內容與修改範圍後, 明確要求 `write=true`, 中途檔案被修改時需重新讀取與合併

Tool: `update_markdown`

```json
{
  "target": "C:\\path\\documents\\guide.md",
  "heading": "## 使用方式",
  "content": "## 使用方式\n\n這是新的章節內容\n",
  "expected_sha256": "<inspect_markdown 回傳的 sha256>",
  "write": false
}
```

範例中的 `<inspect_markdown 回傳的 sha256>` 必須換成工具回傳的 64 位十六進位 hash, 不可照貼, content 必須以相同標題開頭, 不能插入同層或更高層章節, 篇幅上限 200000 字元

預覽的 `next_sha256` 是候選內容 hash, 尚未寫入時, 正式套用仍使用原本的 `expected_sha256`; `status=written` 表示已寫入並讀回核對, `unchanged` 表示不需寫入, 工具保留既有 UTF-8 BOM, 換行格式與無關章節

## 追加唯一紀錄

Tool: `update_markdown`

```json
{
  "target": "C:\\path\\documents\\history.md",
  "entry_id": "review-001",
  "content": "已確認本次文件擷取與章節內容\n",
  "expected_sha256": "<inspect_markdown 回傳的 sha256>",
  "write": false
}
```

`heading` 與 `entry_id` 必須擇一, 相同 entry ID 與內容再次執行不重複追加, 相同 ID 配上不同內容會拒絕, 每次都先取得目標目前的 SHA-256, 再預覽與明確套用

## 常見問題

| 情況 | 處理方式 |
| --- | --- |
| 工具清單沒有 `local_documents` | 依安裝文件確認設定與環境, 重新載入 client, 核對五個工具名稱 |
| `missing_dependencies` 或 OCR model missing | 在指定 runtime 安裝 server wheel 與相依套件, 再執行 pip check, 原始碼維護者亦可使用 requirements.txt, 不在工具呼叫時臨時下載 |
| Path is outside the configured roots | 確認真實路徑在允許的範圍, 如需新增範圍, 明確透過 installer 重新註冊 |
| Stale SHA-256 | 重新 inspect 並合併新內容, 不停用 hash guard |
| Existing output requires its current SHA-256 | 取得既有 output 的 SHA-256, 或選擇另一個明確的新檔名 |
| `partial` 或 `truncated` | 檢視失敗與省略記錄, 必要時分批 OCR, 將 `max_chars` 提高至最多 200000, 或明確寫出完整 output |
| 核心套件缺少或 API 不相容 | 在同一 runtime 安裝相容的核心 wheel, 檢查套件版本後重新啟動 |
| 雲端 placeholder 無法原子取代 | 先確認本機檔案狀態, 確有需要時, 明確使用 `in_place=true` 備援, 會建立備份 |

Markdown 預覽與寫入的目標都須位於 write root, 存取範圍由啟動設定指定. Notion 同步、Git 操作與程式編譯使用各自入口

文件與 Markdown CLI、versioned core 及 MCP 的安裝與驗證入口見 [文件工具](../../python-tools/README.md)
