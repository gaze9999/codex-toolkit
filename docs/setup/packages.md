# MCP Wheel 安裝包

提供可個別安裝的 Python MCP wheel 與跨平台安裝工具. 安裝工具收錄完整工具清單, 依選定項目處理 Python / Node.js 套件, native app 或 hosted MCP 註冊

從 [GitHub Releases](https://github.com/gaze9999/codex-toolkit/releases) 下載 `mcp-installers-<tag>.zip` 並解壓, Windows 執行 `launch-cli.cmd mcp`, macOS / Linux 執行 `sh launch-cli.sh mcp`. 選單每次處理一項工具, Python server 優先使用隨包附上的 wheel, 其他必要相依依平台與該工具的 requirements 安裝

選單預設使用繁體中文台灣用語, 輸出編碼無法表示中文時自動使用英文. 類別選單輸入 `L` 可選擇中文或英文, 也可用 `launch-cli.cmd mcp --lang en`, `sh launch-cli.sh mcp --lang en` 或 `codex-mcp-setup --lang en` 指定英文, `--lang zh-TW` 指定中文, `--lang auto` 採中文優先與編碼 fallback, PowerShell 個別工具入口使用 `-Language en`. 自動判斷依輸出編碼, 字型缺字或終端機顯示異常時可手動選英文

類別選單的「顯示目前用途的全部工具」顯示目前 profile 的全部工具, 預設 `all` 顯示完整清單. 工具清單輸入 `0` 或按 Enter 返回類別, 類別選單輸入 `0` 顯示全部, `Q` 或 Enter 離開. 完成安裝或遇到人工設定, 檢查缺項及錯誤時, 互動入口會直接開啟[中文設定指引](installer-guide.html), 不等待按 Enter. 指定工具啟動也適用, `--yes`, `--list`, 非互動輸入及 `--no-guide` 不自動開啟指引, 舊參數 `--no-pause` 沿用相同行為, Windows PowerShell 個別入口使用 `-NoGuide`. 指引固定使用繁體中文台灣用語, 與選單語言分開. 自動開啟失敗時顯示檔案位置, 原本的檢查 / 安裝退出狀態保留

也可個別下載 wheel, 安裝 `codex_tool_setup-0.4.0-py3-none-any.whl` 後使用選單:

```text
python -m pip install codex_tool_setup-0.4.0-py3-none-any.whl
codex-setup --list
codex-setup skills --list
codex-mcp-setup
codex-tool-setup --tool arxiv --wheel-dir <absolute-wheel-directory>
```

`--wheel-dir` 可指向安裝包解壓後的 `wheels` 資料夾, 其中包含 wheels 與 `mcp-release-manifest.json`. 安裝前核對選定套件的版本與 SHA-256, 每個 MCP 使用獨立環境. Python, browser, 帳戶, API key, notebook, project 或檔案範圍依各項條件設定

| Wheel | 用途與相依 |
| --- | --- |
| `codex-tool-setup` | 依用途分類的安裝選單, checker, 單項 updater 與完整工具設定, Python 3.11+ |
| `codex-jev-mcp` | Jev 評分與 context 排序, 需帳戶環境變數 |
| `codex-local-documents-mcp` | 本機文件擷取與 Markdown, 需對應 document core |
| `codex-workspace-inspection-mcp` | 唯讀工作區檢查, 需對應 workspace core |
| `codex-development-tools-mcp` | RTK / cmux adapter, 需各自的 native executable |
| `codex-edge-devtools-mcp` | Codex 的 Edge 除錯, wheel 內含官方 DevTools MCP 1.10.1, 需 Node.js 與已安裝 Edge |
| `arxiv-mcp-server` | 論文搜尋與閱讀 |
| `reddit-rss-mcp` | Reddit 公開 RSS |
| `serena-agent` | 程式碼 symbol / references, 1.7.0, Python 3.11+, 各語言 server 另檢查 |
| `excel-mcp-server` | Excel 工作簿操作 |
| `markitdown-mcp` | PDF / Office 轉 Markdown, 格式支援依上游 extras |
| `jupyter-mcp-server` | Notebook 操作, 需先選定 notebook 與執行範圍 |
| `jisho-mcp` | 日文查詞 |
| `igdb-mcp-server` | 遊戲資料查詢, Python 3.12+ 與帳戶 credentials |
| `mcp-taiwan-price-compare` | 台灣購物比價, Python 3.13+ |
| `j-quants-doc-mcp` | J-Quants API 文件 |
| `roc-cwa-mcp` | 氣象署 3 天 / 一週預報, 使用本機 `CWA_API_KEY` |

需要額外 app, notebook, project 或操作範圍的項目會顯示 manual setup. 個別 wheel 可安裝至所屬環境, 完成該項設定後再註冊及呼叫 MCP

所有工具的分類, 接法, 相依與更新規則都包含於 setup wheel, Python server 提供獨立 wheel, Node / native / hosted 工具依原平台安裝或註冊. `--profile development` 可篩選開發電腦的選單, `codex-tool-update --tool <name>` 查該項新版, `--apply` 更新, 詳細方式見 [分類與工具更新](../tools/workflows.md). 不需要安裝完整 repository, 各工具的帳戶與 runtime 仍分開建立

Edge 除錯選 `edge-devtools`, 可執行 `launch-cli.cmd mcp edge-devtools`, 或使用 `codex-tool-setup --tool edge-devtools --interface mcp --wheel-dir <absolute-wheel-directory> --apply`. 安裝後新增 Codex 的 `edge_devtools` entry, 重新載入 client 才能核對工具可用狀態. Wheel 已包含固定版本的官方 JavaScript runtime 與授權, 啟動時不需要 npm 下載, 預設使用 headless Edge 與隔離 profile. 詳細相依與既有 session 的明確串接方式見 [Edge DevTools MCP](../../mcp/mcp_servers/edge_devtools/README.md)

Context7, Notion, Todoist 等 hosted MCP 由安裝工具保存連線設定, Playwright, Anki, 圖表工具等沿用 Node.js 套件, RepoPrompt 與工作台依平台安裝 native app. 接法與來源見 [完整工具介紹](https://github.com/gaze9999/codex-toolkit/blob/main/docs/tools/catalog.md)

第三方 wheel 使用固定版本的原始 PyPI 檔案, 或固定 commit 的來源建置. CWA wrapper 將環境變數交給原始程式, credential 不放入設定或 OS command line. 授權原文隨 `third-party-notices-<tag>.zip` 與安裝包提供

## CLI 免安裝包

免安裝版正式產檔由 [release workflow](../../.github/workflows/cli-release.yml) 在 Windows 與 macOS 原生 runner 執行, GitHub Release 發布後建置三種 CLI ZIP, 全部原生檢查通過才附加到該 release:

| 平台 | 資產 | 解壓後啟動 |
|---|---|---|
| Windows x64 | `codex-setup-cli-<tag>-windows-x64.zip` | `launch-cli.cmd` / `./launch-cli.ps1` |
| macOS Apple Silicon | `codex-setup-cli-<tag>-macos-arm64.zip` | `launch-cli.command` |
| macOS Intel | `codex-setup-cli-<tag>-macos-x64.zip` | `launch-cli.command` |

每個平台包含獨立 Python runtime、必要解析套件與四類治理及安裝來源, 不需要先安裝 Python 或 Node.js. Windows 使用 `launch-cli.cmd --list` 或 `./launch-cli.ps1 --list`, macOS 使用 `./launch-cli.command --list`, 可選定 `agents`、`skills`、`plugins`、`mcp`, 操作與原儲存庫 CLI 相同. 搬移時保留完整解壓資料夾, 個別 MCP 的 runtime、browser、帳戶與相依依該工具分開處理

Python 固定版本、套件與平台由 [portable requirements](../../mcp/tools/cli-release.requirements.json) 維護, runtime 使用 [uv 維護的可攜 Python](https://docs.astral.sh/uv/guides/install-python/), Python 與套件授權原文隨包保留. 每包保存 `bundle-manifest.json` 逐檔 hash、來源與原生 smoke 結果, 外部 `.sha256` 檔供下載核對, macOS ZIP 保留 executable 權限

[prepare_cli_release.py](../../mcp/scripts/prepare_cli_release.py) 供 Release runner 選定對應平台的 standalone base interpreter, 不使用 virtual environment 當可攜 runtime, 不修改本機 Codex 或系統 PATH:

```text
python mcp/scripts/prepare_cli_release.py --python <standalone-python> --tag <tag> --output dist/cli
python mcp/scripts/prepare_cli_release.py --verify dist/cli/codex-setup-cli-<tag>-windows-x64.zip
```

手動 workflow_dispatch 僅建置測試 artifact, 不上傳 Release. 原生 runner 以包內 runtime 執行入口與四類清單, Windows 同時檢查 CMD、PS1, 確認測試設定未變更. 本機驗證採語法、來源、相依與 CLI 最小檢查, 不執行封裝. 正式產物仍需在各目標電腦驗收操作, macOS 系統下載檔案的信任確認依該電腦處理

## Skills 與發布

- 每個 Skill 獨立使用 SemVer, `SKILL.md` 的 `metadata.version` 保存 `0.4.12` 等版本, 修正文案或相容錯誤增加 patch, 增加相容能力增加 minor, 不相容的呼叫或輸出規格變動增加 major. 整包 release Tag 另行管理, 未改動的 Skill 保留版本, `metadata.author` 與 `metadata.repository` 保存公開署名及來源連結
- 技能介面的版本放在 `agents/openai.yaml` 的 `interface.display_name`, 例如 `Coding Prompt (v0.4.7)`, `metadata.version` 保留作為版本來源, 不改 `SKILL.md` 的 `name` 或 `$skill-name` 呼叫方式. Codex 的 [UI metadata 規格](https://learn.chatgpt.com/docs/build-skills#optional-metadata)提供顯示名稱, 未列出獨立的版本顯示欄位, 本機同步後若未顯示更新, 重新啟動 Codex
- 每個 release 的 Skills 只提供一份 `all-skills-<tag>.zip` 組合包, 不再產生個別 Skill ZIP, 舊 release 資產保留
- 整合 ZIP 的頂層直接放各 Skill 目錄, 不增加外層 `skills/`, 也不包入個別 ZIP

[Agent Skills 規格](https://agentskills.io/specification)允許在 metadata 保存版本, 未指定統一格式. 社群的[版本與封裝提案](https://github.com/agentskills/agentskills/discussions/302)討論個別版本與 CalVer, 目前本包沿用既有版本序列並採用 [SemVer 2.0](https://semver.org/), Git Tag 的 `v` 前綴保留

## Plugin 發布

Plugin 來源映射、可封裝項目與 Marketplace 組合包由獨立 Release workflow 處理, 詳見 [Plugins](../plugins.md). `prepare_plugin_release.py --check` 只做記憶體內檢查, 不封裝. 來源定義不代表已通過安裝、啟用、離線或移除驗收

## 自動版本與 ZIP

在 repository 根目錄執行 [prepare_release.py](../../mcp/scripts/prepare_release.py), 使用 Python 3.10 以上, 不需安裝額外套件:

```powershell
# 本機 Git Tag 的最高版本 +0.0.1, 不變更個別 Skill 版本
python mcp/scripts/prepare_release.py

# 手動指定版本, 也接受 v0.5.0
python mcp/scripts/prepare_release.py --version 0.5.0

# 只預覽, 不改版本或產生檔案
python mcp/scripts/prepare_release.py --dry-run
```

每次執行會動態尋找 `skills/` 下包含 `SKILL.md` 的 Skill 目錄, 保留各 Skill 的版本, 將舊的 `v` 前綴移至顯示名稱, 讓既有 `agents/openai.yaml` 顯示該 Skill 的版本, 取代舊版本後綴而不重複附加, 保留其他 UI metadata, policy 與 dependencies, 並產生:

```text
dist/<tag>/
├── all-skills-<tag>.zip    # 直接包含全部 Skill 目錄及原始檔案
└── release-manifest.json  # 個別 Skill 版本, 當次清單與 ZIP SHA-256
```

- 新增或刪除 Skill 不需改 script, 改名時先同步 `SKILL.md` 的 `name` 與資料夾名稱, 其他引用依需要調整
- 缺少 `metadata` 時會加入初始版本 `0.1.0`, 缺少 author 或 repository 時, 若其他 Skill 只有一種既有值則沿用, 已有值保留
- 沒有任何版本紀錄時從 `v0.0.1` 開始, 整包版本自動遞增只讀本機 Git Tag, 不查遠端 Tag
- ZIP 使用當下 working tree 內容, 包含新增而未提交的檔案, 有 Git 時遵循忽略規則, 並排除常見快取, logs, 暫存及 secret 檔案, `.env.example` 保留
- 封裝後驗證 ZIP 結構, CRC 與逐檔內容, 若同版本重新執行, 只取代此 script 管理且未被另行修改的輸出, 移除該產出目錄中先前 manifest 管理的舊個別 ZIP
- 若封裝後再改 Skill, 用 `--version <same-tag>` 重封裝, 不帶版本會再增加一次 patch
- 可用 `--repo <path>` 指定另一個具有 `skills/` 的 repository, 或以 `--output-dir <path>` 指定輸出根目錄, 每個 Tag 仍有獨立子目錄

發布需當次明確授權, 封裝後核對每個 Skill 的版本與當次 manifest, 只同步已授權的安裝 owner. Plugin Skills 透過原生市集更新, 不另裝同名獨立 Skill, 使用適用的來源 / 鏡像 audit, 個別 Skill 版本不必與整包 Tag 相同

若要半自動發布, 可使用 [release.py](../../mcp/scripts/release.py) 串接準備, 驗證與 GitHub Release, 需要 Python 3.11 以上及已登入的 GitHub CLI. 首次建置先在隔離 Python 環境安裝 [發布相依清單](../../mcp/tools/release.requirements.txt), 清單依固定來源的 build-system 與 Jev 稽核相依維護:

```powershell
python -m pip install -r mcp/tools/release.requirements.txt
python mcp/scripts/release.py prepare --dry-run
python mcp/scripts/release.py prepare                 # 或加 --version 0.5.0
# 檢查 diff 與 dist/<tag>/release-manifest.json, 自行 commit 預定發布的變更
python mcp/scripts/release.py publish <tag>
```

若 sandbox 與 GitHub CLI 使用不同檔案權限, `prepare` 與 `publish` 可傳入同一個 `--asset-root /absolute/release-assets`, Skill assets 會放在 `<asset-root>/<tag>`, MCP wheel 會放在 `<asset-root>/mcp/<tag>`, 仍執行相同來源與 hash 核對

`prepare` 提供版本與 Skill ZIP 封裝, 並以 [prepare_mcp_release.py](../../mcp/scripts/prepare_mcp_release.py) 在隔離副本建置本機 adapters, Jev 與安裝工具 wheel, 加入固定版本的第三方 Python MCP, 跨平台安裝包與第三方授權包. `publish` 同時附上 `mcp-release-manifest.json`, 供 setup 更新入口核對 wheel 版本與 checksum, 並推送已提交的分支與建立 GitHub Release, 發布前要求乾淨的 working tree, 分支追蹤 `origin` 同名分支, 且 Tag 尚不存在

## GitHub 版本與發布判斷

`cp` 只提交及推送, 不建立 Tag / Release. `cpr` 或明確發布要求才沿專案流程交付, 準備封裝、修改 metadata 或更新本機外掛不代表已發布

版本號與發布時機分開判斷. 採 [SemVer](https://semver.org/lang/zh-TW/) 時, 不相容介面變更用 major, 相容的新功能用 minor, 相容修正用 patch, 初始 0.x 階段另依既有穩定性政策. Git Tag 可用 `vX.Y.Z`, 套件欄位遵循自身格式, Python 依其版本規則. Skill、Plugin、Python 套件及整包版本各自管理, 不因無關 CI / 文件修改整批升版

依實際使用者影響及交付需求安排發布, 不限定只有 major / minor 才能發, 也不每次修改都自動發. [VS Code 的歷史流程](https://github.com/microsoft/vscode/wiki/Release-Process)示範驗證後以 patch 交付修正, [Hatch 發布](https://github.com/pypa/hatch/releases)提供分版變更說明, 可參考而不照搬分支與週期. [社群討論](https://www.reddit.com/r/AskProgramming/comments/1vkn207/in_semver_do_you_draw_a_line_as_to_which_ci/)也區分產品版本與 CI 修改, 屬情境意見, 相容性仍回查正式規格

發布前依當次產物核對 README 的安裝 / 使用 / 相容性、metadata / Tag / commit、LICENSE 與必要第三方 notices、必要 CI、資產及變更說明. 既有 MIT 不變, 公開可讀不等於可重新散布. SECURITY、CONTRIBUTING、CODE_OF_CONDUCT、templates、citation 或 changelog 依用途補充, [GitHub 社群檢查表](https://docs.github.com/en/communities/setting-up-your-project-for-healthy-contributions/about-community-profiles-for-public-repositories)不是全部專案的發布門檻

[GitHub 自動變更說明](https://docs.github.com/en/repositories/releasing-projects-on-github/automatically-generated-release-notes)可作草稿, 仍需補直接提交、使用者影響、遷移及已知限制. GitHub 自動提供的 source ZIP 與可執行安裝包分開驗收, 推送、Tag、Release、資產上傳及下載 hash 各自回報

使用 [immutable releases](https://docs.github.com/en/code-security/concepts/supply-chain-security/immutable-releases) 時先建 draft、附齊資產再發布. 本專案目前 CLI workflow 於 `release.published` 後補資產, 啟用 immutable 前須先處理流程相容性, 本次不修改 GitHub 設定. 同版本本機重封裝不代表可替換已發布內容, 正式內容變更用新版本

來源核對日期: 2026-10-07
