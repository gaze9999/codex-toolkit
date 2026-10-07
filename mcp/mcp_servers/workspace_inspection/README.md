# Workspace Inspection MCP

唯讀查詢驗證證據及比對兩個 Skills, 環境或鏡像資料夾, 確定性處理由 `my-py-workspace-core` 提供, MCP 只負責 schema, 路徑範圍與錯誤轉換

工具:

- `workspace_status`: 版本與可讀範圍
- `validation_evidence`: 索引既有 `run-*/results.json`, 不重新執行驗證命令
- `compare_environment`: 依相對路徑, 大小及 SHA-256 比對兩個目錄, 不同步或修改檔案

預設排除 VCS 內容, cache, `.env`, credentials 及 key 檔, 如需不同範圍, 必須由呼叫端明確提供 include / exclude, Skill 仍負責判斷差異是否應同步

```text
python -I -B -m workspace_inspection_mcp.server --read-root /absolute/workspaces
python -I -B -m workspace_inspection_mcp.verify
```
