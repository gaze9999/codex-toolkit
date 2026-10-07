# Jev MCP 操作教學

Jev 用於已整理候選的語意排序與有限分類, 文件搜尋, 必讀規格保留, 最終判斷與驗證仍由 Main 負責, 先依 [安裝說明](../setup/cli.md) 註冊, 詳細 API 與 CLI 說明見 [既有 usage reference](../../skills/jev-evaluation/references/usage.md)

MCP 與 Skill 實作維持在 `codex-setup/skills/jev-evaluation/`, 各專案共用同一份使用者層級設定, 不在每個 repo 建立另一份 server

## 何時值得使用

先完成本地搜尋與來源版本, 狀態及相依篩選, 仍有多份可能相關的段落需排閱讀順序, 或候選摘要需依明確分類/評分標準比較時, 才考慮 Jev. 候選少, 順序已定或現有規則足以決定時直接由 Main 處理, 不把 Jev 當成每輪前置檢查

跨文件/歷史證據排序, 工作項目分類與共用工具候選比較的邊界見 [Skill 使用情境](../../skills/jev-evaluation/references/usage.md#when-to-use-jev). Jev 不決定項目已完成, 可開工或規格衝突採哪一方, 也不替代程式等價, 權限, hash 與 Test 驗證, 全面檢查仍須涵蓋全部要求

query, rubric 與候選摘要都需符合外傳授權, 改成摘要或移除個資不代表自動獲准. 排序後先讀相關 Markdown 抽出版, 需要畫面證據, 缺漏/疑義/版本衝突或明確原始來源核對時才回查原檔

## 呼叫原則

一次問一個可明確判斷的語意條件, 選項與 criteria 保持一致, 缺少資訊時保留 unknown, 計數, 日期先後, 版本與 ID 比較交給程式. 同一批必要 state 的獨立問題才合併, 不為 batch 塞入無關全文, rank helper 已合併 optional candidates, 不需要再逐筆呼叫

新的 rubric, model 或繁體中文情境先以可外傳且有預期答案的代表案例檢查, confidence 不代表事實正確率. 相同輸入與規則的結果可在當次工作重用, 來源改變則重查, 不新增例行輪詢或每輪評分. 完整設計邊界見 [question design](../../skills/jev-evaluation/references/usage.md#question-design-and-call-cost), 可分享的說明另見 [Codex Playbook](https://github.com/gaze9999/codex-playbook)

## 如何辨識實際使用

| 紀錄 | 能證明的範圍 |
| --- | --- |
| 已安裝/註冊 | 設定存在, 不代表目前對話已載入 |
| `jev_status` 或 required-only 離線驗證 | 本機狀態或 MCP 通道, 沒有對工作候選做遠端評分 |
| `jev_rank` / `jev_evaluate` 回傳 `status=ok` | 該次語意比較完成, 不代表 Main 已接受結果或程式驗證通過 |
| `status=fallback` / `skipped` / `dry-run` | 未完成遠端語意比較, 依實際狀態繼續原流程 |

實際使用後簡短說明用途, tool/status 與 Main 採用方式或 fallback, 回應有 model 才記錄實際 model. 不預設新增永久 log, 不貼輸入內容或 Key, 未使用的原因僅在使用者詢問或與本次評估相關時說明

## 需要診斷時檢查本機狀態

可以對 Codex 說:

```text
請呼叫 Jev 的 jev_status, online 設為 false, 只檢查目前本機設定, 不送出候選或問題
```

Tool: `jev_status`

```json
{
  "online": false
}
```

`online=false` 不呼叫 API, credential 缺少時會回報 fallback, 不顯示 Key, `online=true` 才查詢遠端 model 可用性, 此查詢不提交專案內容, 也不證明評分品質

Key 透過既有 `TYPESAFE_API_KEY` 或本機 credential file 提供, 不放進工具參數或對話, 首次設定方式見 [Jev 安裝文件](../../skills/jev-evaluation/README.md)

## 排序已找到的候選

先用搜尋或程式碼工具取得小範圍候選, 再提供已允許外傳的精簡摘要, Jev 不會自行掃描 repo, 開啟檔案或讀取聊天歷史

Tool: `jev_rank`

```json
{
  "query": "Where is form validation implemented?",
  "candidates": [
    {"id": "governing-spec", "required": true},
    {"id": "candidate-a", "text": "A local validator checks required fields before submission."},
    {"id": "candidate-b", "text": "Theme preferences select page colors."}
  ]
}
```

此範例包含一般候選, 真正呼叫 MCP 時會將 query 與非 required 候選送到 Jev API, 這些內容需先符合目前專案的外傳授權

- `id` 必須唯一, 使用不含來源路徑的識別值, ID 與原始來源的對照留在 Main
- `required=true` 的 ID 在本機保留, 不把它的 text 送去評分, 必讀規格不依排序結果刪除
- 其他候選依 probability 排序, 每個候選仍保留, probability 是語意相關性訊號, 不代表程式或規格正確率
- `status=fallback` 時保留原順序與 ID, probability 為 null, Main 繼續用原有工具處理

可以對 Codex 說:

```text
請先用本機搜尋找出與表單驗證相關的候選, 保留必讀規格; 若候選摘要已獲准外傳, 再使用 Jev 排序閱讀順序, 不依分數刪除候選或縮減驗證
```

若所有候選都是 required, 工具會回傳 `status=skipped`, 不需要 Key 或 API, 可用這個例子檢查離線工具流程:

Tool: `jev_rank`

```json
{
  "query": "Retain mandatory guidance",
  "candidates": [
    {"id": "governing-spec", "required": true}
  ]
}
```

## 有限分類或評分

`jev_evaluate` 接收明確 state 與命名 questions, 真正呼叫會提交到 Jev API, 只提供完成分類所需且已允許外傳的內容

Tool: `jev_evaluate`

```json
{
  "state": "The request asks to rename a documentation heading.",
  "questions": {
    "category": {
      "type": "choice",
      "instructions": "Which description best matches the stated request?",
      "criteria": {
        "documentation": "Text editing",
        "implementation": "Application behavior",
        "unclear": "Insufficient detail"
      }
    }
  }
}
```

| Question type | 輸入與用途 |
| --- | --- |
| `noul` | 判斷是否符合描述, criteria 可提供 true/false 的定義, 回傳 0-1 probability |
| `choice` | criteria 是命名選項與描述的物件, 選擇其中一項 |
| `score` | criteria 是由低到高排列的 2-10 個等級描述, 回傳帶 legend 的加權分數 |

成功時檢查 `status=ok`, `answers`, 回應的 `model` 與 `usage`, Main 仍需核對實際規格與程式碼, 不把 Jev 的輸出當成批准寫入或跳過測試的授權

MCP 沒有 `dry_run` 參數, 要先檢查 rank 或 evaluate JSON 格式而不連線, 在已安裝 Skill 根目錄使用 CLI:

```text
python -B scripts/jev.py rank --input candidates.json --dry-run
python -B scripts/jev.py evaluate --input evaluation.json --dry-run
```

macOS/Linux 可使用已確認的 `python3`, CLI 參數與 MCP 工具參數不能混用

## Model 與結果限制

工具可省略 `model`, 此時沿用 `TYPESAFE_MODEL` 或 client 預設 `jev-latest`, 特定工作流程需要固定版本時, 先確認可用性與實測結果, 再明確指定

保留回應實際 model, 不只記錄請求名稱, 中文與混合技術名稱的排序效果需以代表案例評估, 不從單一範例推論, confidence 與 probability 都不等於需求正確性保證

## 常見問題

| 情況 | 處理方式 |
| --- | --- |
| 工具清單沒有 Jev | 確認使用者層級設定, 重新載入 client, 核對 `jev_rank`, `jev_evaluate`, `jev_status` |
| 本機 status 回報 credential 缺少 | 依 Skill 安裝文件設定 Key, 不貼入對話或 source |
| API 或驗證失敗, `status=fallback` | 保留原候選與既有流程, 查看 reason, 不因此判定應用程式有缺陷 |
| request/response 超出 64 KiB client 上限 | 縮小或分批處理非必讀摘要, 必讀內容仍由 Main 保留 |
| question type 或 criteria 不合法 | 先使用 CLI `--dry-run` 核對, 不臆造新的 tool 參數 |
| 排序與實際內容不一致 | 回看來源, 以規格與確定性驗證為準, 不自動採納分數 |

這是本機 stdio MCP, 本套件不提供公開 HTTPS endpoint, 其他系統是否可用需確認其 MCP client 能力, 各台電腦的 runtime 與 credential 分別安裝

## Wheel 與選用本機監看

新版 `codex-jev-mcp` wheel 與 Skill 使用同一份 Python client, 可從任意工作目錄以 `python -I -B -m codex_jev_mcp.mcp_server` 啟動, baseline bundle 安裝方式見 [統一安裝入口](../setup/cli.md), 原 Skill installer 仍可使用

永久紀錄預設關閉, 明確需要時, 安裝獨立的 `local-activity-monitor`, 使用 `--enable-jev --configure-only` 啟用, 再以 `--codex --open` 開啟本機頁面, 停用使用 `--disable-jev --configure-only`, 舊 MCP process 需重新載入新版 client

只保存時間, operation/source, model, known tokens, latency, HTTP attempts 與 body bytes/status, 不保存 query, rubric, candidates, state, answers, Key, header 或 raw error, telemetry 失敗不改變 Jev 結果, 未知 token 保留為 null, 畫面標示本機觀察統計, 不代表帳戶總用量, 額度或費用, 同一操作與 HTTP 重試分開計數
