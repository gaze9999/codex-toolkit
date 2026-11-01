# Decisions 開發評估工具

提供相同核心的 CLI 與選配 STDIO MCP, 用於有明確問題、有限候選與獲准證據的開發判斷
需要 Python 3.11+, 核心只用標準函式庫, MCP 另外使用 mcp 2.2.0

## 安裝與離線使用

在此套件目錄執行, 建議使用獨立虛擬環境

```sh
python -m pip install ".[mcp]"
decisions status
decisions validate --input example.json
```

`example.json` 使用官方欄位, 例如:

```json
{"input":"Two independent modules have owners and separate checks.","questions":[{"type":"predicate","name":"independent","instructions":"Does the evidence establish independently verifiable work?"}]}
```

`status` 只檢查選定環境變數是否有值, 不證明金鑰有效, 未設定時以 exit 1 回傳 `needs_credentials`
`validate` 不連線, 只回傳模型、問題數、bytes 與 SHA-256, 不回傳證據內容

## 手動設定認證

一般本機使用由你在私人環境設定 `OPENAI_API_KEY`, 再重新啟動使用該環境的 CLI / MCP
工具不建立金鑰、不讀 Codex auth.json、ChatGPT 登入或其他供應商憑證, 不自動讀取 .env
設定完成且本次資料傳輸與費用已獲授權後執行:

```sh
decisions evaluate --input example.json --approved
```

官方另支援 Workload Identity Federation, 需要 Platform 身分提供者與服務帳號映射, 並非個人 ChatGPT 帳號綁定
若已有獲准的短期 token 提供流程, 可明確使用以下非機敏設定, token 由外部流程更新後重啟 MCP
本工具不執行 token exchange 或自動更新 token

```json
{"credential_env":"OPENAI_ACCESS_TOKEN","model":"gpt-6-luna","timeout_seconds":20}
```

```sh
decisions --config settings.json status
decisions-mcp --config settings.json
```

設定 JSON 只接受 `credential_env`、`model`、`timeout_seconds`, 不接受金鑰值或自訂 API 網址
預設 gpt-6-luna, 實作支援模型明確限制於官方目前列出的此模型, 不自動切換

## MCP 與資料格式

在 Codex 的 MCP 設定指定實際虛擬環境可執行檔, 不需 Playground

```toml
[mcp_servers.decisions]
command = "/absolute/venv/bin/decisions-mcp"
args = ["--config", "/absolute/private/settings.json"]
env_vars = ["OPENAI_API_KEY"]
```

Windows 使用實際 `Scripts/decisions-mcp.exe` 路徑, 若選 access token 則將 env_vars 改成該變數
工具為 `decisions_status`、`decisions_validate(request)`、`decisions_evaluate(request, approved=false)`
`approved=true` 表示呼叫端已確認本次授權, 不會自行取得授權

| 項目 | 本版支援與界線 |
| --- | --- |
| Endpoint | POST https://api.openai.com/v1/decisions, 每次 evaluate 最多 1 個請求, 無重試與跨供應商 fallback |
| input | 非空文字或 1 至 64 個 user / developer / system message, 不含 tool history |
| content | input_text, user 可用 input_json / input_image, 不支援 file ID |
| 圖片 | PNG / JPEG / WebP base64 data URL 或 HTTPS URL, 不讀本機圖片路徑, 不在本機下載遠端圖 |
| questions | 1 至 400, 每題必須有唯一 name、type、instructions |
| predicate | 回傳 probability |
| choice | 2 至 255 個唯一 typed value, 字串與 boolean 分開比對 |
| score | 2 至 10 個唯一 label, score 為索引的機率加權值 |
| 本機限制 | 請求 2 MiB, 單段文字 65536 字元, JSON evidence 256 KiB / 32 層 / 10000 值, 回應 2 MiB |
| 逾時 | 預設 20 秒, 可設 1 至 60 秒 |
| 回應 | 保留 provider response、usage、request ID, 區分 ok、partial_refusal、refused、invalid_response、http_error、transport_error |

官方 API 的完整功能比此 adapter 廣, 本版拒絕不支援欄位, 不靜默丟棄或改寫
評估失敗回 Main, refusal 不是通過, unknown 應由題目明確提供候選
不把不同供應商的機率與信心轉成共同分數, 不用評分取代測試、授權或驗收
原始回應可能包含輸入中出現的標籤, 呼叫端仍需依資料邊界保存結果

## 驗證與官方來源

```sh
python -m unittest discover -s tests -v
```

離線 synthetic transport 測試不連線且不讀真實金鑰, 實際 API 與帳務驗證另行執行
費用與支援模型採 [Decisions 指南](https://developers.openai.com/api/docs/guides/decisions), 欄位採 [API reference](https://developers.openai.com/api/reference/resources/decisions/methods/create)
認證依 [API authentication](https://developers.openai.com/api/reference/overview#authentication) 與 [Workload Identity Federation](https://developers.openai.com/api/docs/guides/workload-identity-federation), 查核日期 2026-11-01
