# MCP 與安裝包原始碼

根目錄 `mcp/` 保存 MCP adapter、封裝專案、安裝實作與相依來源, 工具是否可用仍需核對目前 Codex session

| 路徑 | 內容 |
|---|---|
| `mcp/mcp_servers/` | MCP adapter、wheel 專案與 baseline preset, 保留 Python 模組名稱 |
| `mcp/scripts/` | CLI 安裝、同步、驗證與封裝, `launch/` 保存平台啟動流程 |
| `mcp/tools/` | requirements、版本與校對規則 |
| `mcp/third_party/` | 第三方授權原文 |
| `mcp/pyproject.toml` | Local Documents wheel 專案 |

| 目錄 | 責任 |
|---|---|
| local_documents | 文件擷取與受限 Markdown 操作, 依賴 versioned `my-py-document-core` |
| workspace_inspection | 唯讀環境比對與證據檢視, 依賴 `my-py-workspace-core` |
| development_tools | RTK / cmux 的 MCP adapter |
| edge_devtools | 固定上游來源的 Edge DevTools wheel 與啟動器 |
| tool_setup | CLI 安裝管理包, 保存 installer、治理與 Skill 資源 |
| cwa_extended | 天氣服務上游封裝用啟動器 |
| presets | baseline server、套件版本與工具清單 |

Jev 的 MCP 與 CLI 隨 [jev-evaluation Skill](../skills/jev-evaluation/README.md) 維護. 註冊、runtime、帳戶與實際呼叫分別驗證, 使用 [CLI](setup/cli.md) 單項處理, [安裝包](setup/packages.md) 說明 wheel / ZIP
