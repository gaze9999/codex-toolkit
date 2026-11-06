# 跨工作區產出物盤點

在本機盤點選定工作區與其 Git 工作樹, 產生離線 HTML 與 JSON, 需要清理時再依勾選清單永久刪除

```sh
cargo build --release --locked
agent-artifact-audit scan --workspace PROJECTS --codex-home CODEX_HOME --claude-home CLAUDE_HOME --out REPORTS
agent-artifact-audit apply --report SCAN_JSON --selection EXPORTED_SELECTION --out REPORTS
agent-artifact-audit report --run CHANGE_RUN
```

將對應平台的執行檔放在用戶端可找到的 PATH, 使用已建置的執行檔時免安裝 Rust, 工作樹探索與可刪資格重查需要 Git  
可重複指定 `--workspace`, 工具目錄預設使用 `CODEX_HOME`、`CLAUDE_CONFIG_DIR` 或家目錄中的 `.codex`、`.claude`, 報表輸出請指定獨立目錄, 列入的外部工作樹可在掃描範圍核對

## 分類與選取

版本 1 的 `backup-name`、`build-name`、`temporary-name` 只辨識名稱, 備份與用途未知的項目保留供檢閱  
`setup-rotation` 辨識已指定工具目錄中 Setup 安裝器的 Global 備份, 只開放選取現行檔案與較新同名備份均存在、位於 Git 儲存庫外的舊備份檔, 仍需由使用者決定是否保留歷史版本
`python-cache` 僅在已確認的工作樹中開放選取 Git 忽略且未追蹤的 `__pycache__`, 每個成員必須是具有對應原始碼的 CPython 位元組碼, 工具資料目錄受到保護  
盤點檔案大小表示邏輯大小, 巢狀項目各自包含下層資料, 報表顯示的專案產出物可能來自其他工具  
使用篩選器後, 所有已選項目仍列於匯出區, 匯出的 JSON 只含批次與項目 ID, 執行前會核對本機保存的盤點資料

## 執行記錄與復原

每次操作建立批次子目錄, `scan.json` 與 `scan.html` 供檢閱, 實作批次保留 `plan.json`、`events.jsonl` 與獨立變更報表  
同一盤點批次只能執行一次, 要改選項目請重新盤點, 若中斷請讀取本機 `agent-artifact-audit/<批次>.applied` 收據取得原執行目錄, 執行 `report --run` 重建報表  
Windows 本機資料位於 Local AppData, macOS 使用家目錄的 Library/Application Support, 此目錄的寫入權限等同本機使用者  
CLI 結束碼 0 表示完整, 1 表示有缺口或項目未完整刪除且已產生報表, 2 表示呼叫失敗, MCP 摘要使用 `partial` 與報表路徑呈現實際結果

