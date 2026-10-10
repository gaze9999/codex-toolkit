# 治理範例與個人設定

`agents/` 提供通用 Global、subagent 及 Desktop Git 範例. 專案知識保留在適用的專案 `AGENTS.md`, 詳細流程依 [Agent Governance Skill](../skills/agent-governance/SKILL.md) 選用

| 內容 | 位置 | 用途 |
|---|---|---|
| 通用原則範例 | `agents/AGENTS.md` | 選用的 Global 起點 |
| 中性 subagent 設定 | `agents/subagents.config.toml` | 按實際環境選擇 override |
| Desktop 範例 | `agents/desktop-preferences.toml`, `agents/git-instructions.toml` | 預覽後合併必要欄位 |
| 專案 starter | [範本](../skills/agent-governance/assets/project-starter/README.md) | 依專案填入已確認事實 |
| 元件維護 | [維護指引](../skills/agent-governance/references/component-authoring.md) | 指令、參考、Python、Plugin 與 MCP 分工 |

個人偏好、帳戶設定與機器狀態保留在私人設定來源. 公開範例不包含作者的 Global 全文、ChatGPT profile、個人 model pin 或安裝狀態

Setup CLI 可列出來源與預覽單項差異, 不需套用所有設定

Global 安裝器選取來源的 `AGENTS.md`、`subagents.config.toml` 及可選 `references/` 內的 Markdown, 保留巢狀相對路徑. 參考文件由指示按需引用, 避免加入每次載入的全文. 非 Markdown 與目標既有的其他檔案保留原狀

```text
python mcp/scripts/install_global_agents.py --source-root /path/to/private/agents
python mcp/scripts/install_global_agents.py --source-root /path/to/private/agents --install
```

預覽不寫入, 任何內容衝突都會停止整批套用. 已核對後用 `--install --replace` 先備份再取代, 備份保留相對路徑. 來源參考文件或目標路徑含 symbolic link / junction 時停止並列出位置, 避免沿連結讀寫其他目錄

```text
launch-cli.cmd agents --list
launch-cli.cmd agents global
launch-cli.cmd desktop
```

macOS / Linux 用 `sh launch-cli.sh` 的相同參數. 實際寫入沿選用入口的確認、備份與衝突保護流程, 保留既有設定. Starter 的 memory 預設關閉, 請依需要選擇, 不以範例取代個人決定

內部指令按用途使用精簡繁中或英文, 交付依使用者語言. 來源、安裝內容、client 重新載入與模型行為分開核對
