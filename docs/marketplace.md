# Codex Toolkit 市集

`codex-toolkit` 是 Codex 與 Claude 共用的 Git 市集, `.agents/plugins/marketplace.json` 與 `.claude-plugin/marketplace.json` 指向相同的外掛資料夾
在 Codex 外掛管理介面加入 `gaze9999/codex-toolkit`, 也可使用原生 CLI

```text
codex plugin marketplace add gaze9999/codex-toolkit
codex plugin list --marketplace codex-toolkit --available --json
codex plugin add codex-agent-workflow@codex-toolkit
```

Claude 的自訂 > 外掛程式 > Add > Add marketplace 加入同一個 GitHub 儲存庫, Claude Code 也可使用原生 CLI:

```sh
claude plugin marketplace add https://github.com/gaze9999/codex-toolkit.git --scope user
claude plugin install codex-agent-workflow@codex-toolkit --scope user
claude plugin list --json
```

公開市集提供共用 Skills、工具來源與設定指引, 本機 MCP 依各工具的正式安裝入口另行設定
私人選擇與已準備的 MCP 組合由私人整合包維護, 安裝公開與私人市集時選定單一啟用來源
來源: [Claude 市集格式](https://code.claude.com/docs/en/plugins/marketplace-reference)、[Claude 外掛格式](https://code.claude.com/docs/en/plugins-reference)

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

| 顯示位置 | 正式版本來源 | 更新方式 |
| --- | --- | --- |
| Codex 市集名稱 | 根目錄 `VERSION` | 產生器組合圖案、名稱與版本, `--check` 檢查產生結果是否過期 |
| Claude 市集 | `.claude-plugin/marketplace.json` 的 `version`, 由 `VERSION` 產生 | 原生市集更新後讀取新 metadata |
| Plugin | `plugins/<id>/plugin.json` 的 `version` | Claude manifest 從同一來源產生, 與整包版本分開維護 |
| Skill | `skills/<name>/SKILL.md` 的 `metadata.version` | 依 Skill 內容獨立更新 |

顯示字串不另存一份版號, 修改 `VERSION` 後須執行上述 `--write` 與 `--check`
共用圖案來源為 `assets/branding/toolkit.svg`, PNG 隨外掛封裝, Codex 使用 `logo` / `composerIcon`, Claude 的 `icon` 由同一圖案路徑產生
Codex 市集層使用名稱內的 emoji, 目前原生市集介面未提供獨立圖片欄位

已加入的 Git 市集使用原生更新入口, 指定名稱可只更新該來源:

```sh
codex plugin marketplace upgrade codex-toolkit --json
codex plugin list --marketplace codex-toolkit --json
claude plugin marketplace update codex-toolkit
claude plugin list --json
```

Codex GUI 的市集列可使用升級, Claude GUI 使用 Check for updates
更新後重新載入目的用戶端, 比對原生清單與 manifest, 以實際 Skills 探索確認載入, 顯示名稱與快取路徑作為辨識用途

## 網頁版 MCP

公開目錄與 Skills 可透過 [唯讀市集 MCP](../mcp/marketplace-server/README.md) 提供搜尋、來源讀取及版本核對, Git 市集維持 Plugin 安裝與更新用途

桌面保留原生 Git 市集, Cloud / Web 可使用 Private MCP, 兩端以同一完整 Toolkit commit 驗收, 更新順序、檔案核對與部分失敗處理見 [同版本更新](../mcp/marketplace-server/README.md#git-市集與-private-mcp-同版本更新)

選單技能名稱的 vX.Y.Z 是 Skill 版本, 懸停路徑中的版本是安裝的 Plugin 版本, 整包版本另見根目錄 VERSION, 三者獨立更新
