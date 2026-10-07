# Codex Toolkit 市集

`codex-toolkit` 是 Git 市集來源, root 的 `.agents/plugins/marketplace.json` 指向可獨立安裝的 Plugin. 在支援的 Codex 外掛管理介面加入這份 Git 儲存庫, 也可使用原生 CLI

```text
codex plugin marketplace add gaze9999/codex-toolkit
codex plugin list --marketplace codex-toolkit --json
codex plugin add codex-agent-workflow@codex-toolkit
```

市集加入後可選擇治理、文件、前端、證據、Jev、校對、活動摘要及 README / 授權等外掛. 這是個人可加入的市集, 官方公開目錄上架另有提交流程

Plugin 的 Skills 與資源由來源生成, runtime、帳戶與 MCP 註冊依用途安裝. 既有同名 Skill 若已直接安裝或來自另一個市集, 先選定單一啟用來源, 避免同時使用兩份. 不複製另一台電腦的 venv、client cache 或憑證

| 使用情境 | 操作 |
|---|---|
| Windows / Mac Codex | 加入 Git 市集, 選擇需要的 Plugin |
| 無 Codex 的 Python 使用者 | 使用 [獨立 CLI / 核心](../python-tools/README.md) |
| 需要實際 MCP 工具 | 依 [安裝指引](setup/cli.md) 設定 runtime、權限與帳戶 |
| iPhone / iPad ChatGPT | 依 ChatGPT 當前支援的 Plugin / 遠端 MCP 接入, 本機 stdio runtime 不會直接在手機執行 |

## Python 工具可獨立使用

市集負責安裝工作流程, Python CLI / 核心可從同一公開來源獨立取得, 不需要 Codex 或 MCP. 完整目錄、相依、執行及 core wheel 的用法見 [獨立使用說明](../python-tools/docs/standalone.md)

個人的治理檔、版本與選用項目可保存在私人 profile, 換機使用 [環境還原入口](restore.md)

## 來源與更新

Canonical Skills 在 `skills/`, Plugin manifest / owner 在 `plugins/`. `marketplace/plugins/` 是有來源映射及 SHA-256 的自含散布副本, 不手改生成內容

```text
python -B mcp/scripts/prepare_marketplace.py --check
python -B mcp/scripts/prepare_marketplace.py --write
```

修改來源後生成及核對, 再按 Git / Release 授權交付. Marketplace 變更不代表既有 client 已載入, 需分開確認安裝、啟用、重載與實際使用

參考 [OpenAI Plugin 封裝與市集](https://developers.openai.com/plugins/build/plugins)
