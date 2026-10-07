# Optional Development Tool MCP

本 setup 的窄範圍 stdio adapter, 依 `--tool rtk` 或 `--tool cmux` 只啟用選定工具. 安裝與相依由 [獨立 installer](../../scripts/install_development_tool.py) 及 [requirements](../../tools/development-tools.requirements.json) 維護, 詳細接法見 [optional-mcp.md](../../../docs/tools/catalog.md)

RTK 提供 version status, 既有輸出及明確 read roots 內的 UTF-8 log 過濾, 保留原始 exit code, diagnostics 改動或 filter 失敗時回傳原文. cmux 提供 typed workspace/panel inspection, 建立與 focus 操作, 依既有 macOS CLI 與 socket policy 執行

Python 3.11+, MCP SDK 2.2.0, 每個選定 adapter 使用獨立 user venv. 沒有任意 shell / terminal input, 檔案預設無 read roots. Local adapter 回傳內容仍須符合使用端的資料外傳邊界
