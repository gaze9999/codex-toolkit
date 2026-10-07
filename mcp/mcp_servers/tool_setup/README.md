# Codex Tool Setup

提供工具分類與獨立安裝流程, 包含 hosted MCP, Python / Node.js server, native app, connector, Skill, library 與 API / 網站來源, 清單依包內 requirements 產生

`codex-setup --list` 列出 `agents`、`skills`、`plugins`、`mcp` 四類, 使用 `CATEGORY --list` 查看項目, `codex-setup skills NAME --apply` 預覽單項同步並確認套用, 操作文件集中於包內根目錄的 `docs/`

CLI 需要 Python 3.11+ 與包內宣告的文件解析套件, 未安裝 Python 的 Windows、macOS 電腦可使用 Release 的 CLI 免安裝包, 透過包內 runtime 執行

`codex-mcp-setup` 選擇工具, `codex-tool-setup --tool <name>` 預覽安裝, `codex-tool-check --tool <name>` 檢查相依, `codex-mcp-uninstall <name>` 預覽解除安裝, 需要本機 wheel 時指定 `--wheel-dir <path>`, 每次只處理選定工具及必要相依

`--profile development` 篩選開發電腦清單, 跨分類工具保留單一紀錄, `codex-tool-update --tool <name>` 查選定工具的新版, `--apply` 套用, 已授權的自動執行可加 `--yes`, setup 自身使用獨立 venv 中的 `codex-tool-update --tool setup --apply`, 核對官方 release manifest 與 checksum

各帳戶與環境分別建立 credentials, roots 與登入狀態, 需要原生 App, notebook, project 或檔案範圍的項目會列出人工設定步驟, 移除預設只解除註冊, 共用相依與使用者資料保留
