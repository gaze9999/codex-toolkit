# Codex Toolkit 市集

`codex-toolkit` 是 Git 市集來源, root 的 `.agents/plugins/marketplace.json` 指向可獨立安裝的 Plugin. 在支援的 Codex 外掛管理介面加入這份 Git 儲存庫, 也可使用原生 CLI

```text
codex plugin marketplace add gaze9999/codex-toolkit
codex plugin list --marketplace codex-toolkit --json
codex plugin add codex-agent-workflow@codex-toolkit
```

Windows 若出現 `Filename too long`, Git for Windows 可啟用長路徑, 這項設定影響該使用者的 Git:

```text
git config --global core.longpaths true
```

也可從較短的來源路徑加入本機市集. 支援細節見 [Git for Windows 設定](https://github.com/git-for-windows/git/blob/main/Documentation/config/core.adoc)

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

來源更新後生成並核對市集副本. GitHub 安裝來源在發布後使用原生市集 / Plugin 管理入口更新, 已註冊的本機市集使用限定快照同步, 操作見 [Plugin 更新](plugins.md#已安裝-plugin-更新). 重新載入 Codex 後確認啟用狀態與 Skill discovery

參考 [OpenAI Plugin 封裝與市集](https://developers.openai.com/plugins/build/plugins)

## 圖案與版本

市集顯示名稱為 `🧰 Codex Toolkit v0.4.0`, Toolkit 版本以根目錄 `VERSION` 為準, 各 Plugin 使用自身 `plugin.json` 的版本. 共用圖案的可編輯來源在 `assets/branding/toolkit.svg`, PNG 隨 Plugin 封裝, 不依賴外部圖片服務

市集名稱的圖案使用 emoji, Plugin 清單圖案使用官方 `logo` / `composerIcon` 欄位. 套件與來源更新後, 重新載入用戶端再核對實際畫面
