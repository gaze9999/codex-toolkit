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

```text
launch-cli.cmd agents --list
launch-cli.cmd agents global
launch-cli.cmd desktop
```

macOS / Linux 用 `sh launch-cli.sh` 的相同參數. 實際寫入沿選用入口的確認、備份與衝突保護流程, 保留既有設定. Starter 的 memory 預設關閉, 請依需要選擇, 不以範例取代個人決定

內部指令按用途使用精簡繁中或英文, 交付依使用者語言. 來源、安裝內容、client 重新載入與模型行為分開核對
