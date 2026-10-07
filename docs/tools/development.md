# 按需加入開發工具

可攜 setup 維護工具的接法與啟用條件, 每台電腦依平台, 已安裝能力與核准範圍套用. Global [工具啟用條件](../../agents/AGENTS.md) 保存短版選擇規則

Agent 需要安裝, 設定或診斷其中一項工具時, 使用可用的 [development-tool-setup Skill](../../skills/development-tool-setup/SKILL.md), requirements 與 installer 維持在本 setup, Skill 依當次環境定位來源並核對授權. Angular / Vue Skills 在文件版本或真實 browser 驗證不足時引導相應工具

CLI + Skills / MCP 的選用條件, 官方依據與社群案例見 [cli-or-mcp.md](selection.md), 操作已安裝工具先沿用可完成任務的入口

開發工具的 MCP 模式及生活, 搜尋, 天氣, 研究與領域候選統一見 [optional-mcp.md](catalog.md). 使用 `--interface mcp` 選 Playwright 官方 MCP 或 RTK / cmux adapter, CLI / app 模式仍可獨立沿用, RepoPrompt 的 Windows 路徑保留為 macOS native MCP 接法

## 依缺少的能力選工具

| 需求 | 工具與採用時機 | 平台與接法 |
| --- | --- | --- |
| Library / API 文件不足 | Context7, 先確認 manifests 中的版本, 查相符的官方文件與範例 | Hosted MCP 跨平台, 也可使用官方 CLI / plugin |
| 缺少真實網頁與 UI 驗證 | Playwright, 重現操作並檢查畫面, console 與 network | Windows / macOS / Linux, bounded coding-agent flow 優先 CLI + Skills, CLI 也有 session, 依 client 整合與 introspection 需求選 MCP |
| 瀏覽器效能與 network 問題缺少量測 | Chrome DevTools MCP, 以相同路由與狀態錄製 trace, 檢查 console 與 request | Windows / macOS / Linux, 需相容 Node 與已安裝 Chrome, 隔離 profile |
| 跨檔案程式關係與 references 不清楚 | Serena MCP, 查 symbol 與引用並驗證目標語言支援 | Windows / macOS / Linux, 獨立 Python venv 與語言相依 |
| Test / build / git 輸出過多 | RTK, 同一任務比較原始與過濾輸出後決定是否沿用 | Windows / macOS / Linux, 初期明確使用 CLI prefix |
| 大型 codebase 的 context 選取難以人工檢查 | RepoPrompt CE, 需要檔案選取與 context 預覽介面時使用 | Native macOS, Homebrew app 需要 macOS 14+, source build 需要 macOS 26+ 與相符 Xcode / SDK |
| 多個 CLI session 的視窗, 目錄與通知難以管理 | manaflow-ai/cmux, 需要終端工作區時使用 | Native macOS, Homebrew 或官方 DMG |
| 多 provider / agent thread 的分工與追蹤難以管理 | T3 Code, 需要整合工作台時選用 | Windows / macOS / Linux, 官方 Desktop 或 local web app |
| 多條獨立實作的 branch, worktree 與 review 難以管理 | Conductor, 需要 workspace 隔離與 review 介面時使用 | Mac Desktop, 每個 workspace 使用 Git worktree |

Context7 → Playwright → RTK 表示按缺少的能力逐步加入, 每項只在對應需求發生時使用. RepoPrompt 處理 context 選取, cmux, T3 Code 與 Conductor 依 session / thread / worktree 的實際瓶頸選一個, 先檢查既有 Codex 與終端功能是否足夠

## 相依與首次使用

[requirements 清單](../../mcp/tools/development-tools.requirements.json) 保存每項工具及來源各自的平台, 必要執行檔 / app, 最低版本, 套件版本, 安裝來源及人工檢查項目, Node, native binary 與 Desktop app 由 Python installer 呼叫對應 package manager, Python 套件在所屬獨立環境內安裝

安裝或首次使用前執行唯讀檢查, 需要 Python 3.11+:

```text
python mcp/scripts/check_development_tools.py --tool context7
python mcp/scripts/check_development_tools.py --tool playwright
python mcp/scripts/check_development_tools.py --tool rtk
python mcp/scripts/check_development_tools.py --tool t3code
```

`missing_dependencies` 列出缺少, 過舊或無法讀取版本的必要項目, `unsupported_platform` 表示需換到支援的平台, `manual_verification_required` 表示相依檢查已完成, 還需核對 browser, authentication 或實際互動. 檢查器會讀取選定工具的設定及 app / executable 狀態, 不安裝或修改設定, Context7 另核對有效的 MCP 註冊

## 每次獨立安裝一項

[Python installer](../../mcp/scripts/install_development_tool.py) 的 `--tool` 必填且只接受一項, 沒有全部安裝選項. 預設只顯示選定工具的缺少項目, 來源, 版本, 範圍與用途, `--apply` 顯示清單後詢問安裝, 已明確授權同一清單時可加 `--yes`. 現有符合需求的相依會沿用, 不因指定工具而重裝

```text
python mcp/scripts/install_development_tool.py --tool context7
python mcp/scripts/install_development_tool.py --tool playwright --apply
python mcp/scripts/install_development_tool.py --tool rtk --apply
python mcp/scripts/install_development_tool.py --tool repoprompt --apply
python mcp/scripts/install_development_tool.py --tool cmux --apply
python mcp/scripts/install_development_tool.py --tool t3code --apply
python mcp/scripts/install_development_tool.py --tool conductor --apply
```

以上每一行都是獨立操作, 按當下需求選一行. Windows 選 RepoPrompt, cmux 或 Conductor 時會回報平台不支援並停止. 缺少 package manager 或目前沒有可自動安裝的 runtime 接法時, 先列出需補的項目, 不執行後續安裝

| 工具 | Python 自動安裝接法與相依 |
| --- | --- |
| Context7 | 需要 Codex CLI, 缺少時以使用者 npm prefix 補 CLI 及必要 Node / npm, 再備份並新增單一 MCP entry, 同名不同設定會停止並保留原檔 |
| Playwright | Node.js 18+ / npm, 使用者 npm prefix 安裝 CLI, 缺 browser 時另指定 `--browser chromium`, `chrome`, `msedge`, `firefox` 或 `webkit`, 確認安裝範圍後再執行, Skill 與 UI 驗收依下節核對 |
| Chrome DevTools | 固定官方 npm 1.10.1, Node `^20.19`, `^22.12` 或 `>=23`, 沿用相容 runtime, Chrome 需已安裝, preset 關閉 usage statistics, CrUX lookup 與 update check |
| Edge DevTools | `edge-devtools`, Python 3.11+ 的獨立 wheel 內含官方 MCP 1.10.1, Node `^20.19`, `^22.12` 或 `>=23`, Edge 需已安裝, Codex 使用隔離 profile, DOM / console / network / trace |
| Serena | 固定 PyPI 1.7.0, Python `>=3.11,<3.15`, 獨立 venv, wheel 保留自身 MIT 授權, language server 按實際語言檢查, 不自動開啟 hooks |
| RTK | Windows WinGet user scope, macOS Homebrew, Linux source install 使用已安裝的 Cargo / Rust 1.91+, 缺少時列出相依, 也可依官方 Releases 採預編譯 binary |
| RepoPrompt CE | macOS Homebrew tap 安裝預編譯 app 至 `~/Applications`, 需要 macOS 14+, 沿用官方 cask checksum, source build 的 Python / Git / Xcode 26 與 macOS 26 相依另存清單 |
| cmux | macOS Homebrew tap 安裝 app 至 `~/Applications` |
| T3 Code | 需要 Codex CLI 與登入, Windows WinGet Desktop, macOS Homebrew Desktop 至 `~/Applications`, Linux 使用 Node / npm 安裝 `t3` CLI / local web, 預設 stable |
| Conductor | macOS Homebrew app 至 `~/Applications`, 需要 Git 與 Codex CLI, authentication 及 workspace setup 仍需實際操作 |

npm 安裝位置預設為各平台的 setup user data 目錄下 `mcp/tools/npm`, 可用 `--npm-prefix /absolute/path` 指定. 安裝後輸出應加入 PATH 的位置, installer 只更新本次 process 的 PATH, 使用者可依公司規則設定永久 PATH. Windows 缺 Node / Git 時, WinGet 的預設 scope 可能需要管理員權限, 會先在預覽中列出, 不自動切換企業 package source 或停用 TLS 驗證

## Python runtime 自動補齊

Windows 使用 [CMD 入口](../../launch-cli.cmd), macOS / Linux 使用 [shell 入口](../../launch-cli.sh), 每次指定一項工具. 預設顯示相依與安裝清單, 加上 Apply 後確認安裝. 缺少 Python 3.11+ 時會先詢問 runtime 安裝, 再處理選定工具的必要相依

```cmd
launch-cli.cmd tool playwright
launch-cli.cmd tool playwright -Apply
launch-cli.cmd tool rtk -Apply
launch-cli.cmd tool context7 -Python "C:\approved\python.exe"
```

```sh
sh launch-cli.sh tool playwright --apply
sh launch-cli.sh tool rtk --apply
```

Windows 使用 Python 官方發行的 WinGet `Python.Python.3.13`, scope 為 current user, macOS / 已有 Homebrew 的 Linux 使用 `python@3.13`, Linux 另支援已設定的 apt-get / dnf `python3`, 會先列出 system scope 與 sudo 要求, 安裝後再檢查最低版本. Linux distribution 若只提供較舊 Python, 需改用核准的 3.11+ runtime. 自動 bootstrap 不會安裝全部工具, 也不會因選到不支援的平台而先裝 Python

各平台可明確提供現有 Python, Windows 使用 `-Python`, shell 使用 `CODEX_SETUP_PYTHON=/absolute/python`. 上述 runtime 來源見 [Python on Windows](https://docs.python.org/3/using/windows.html), [WinGet Python 3.13 manifest](https://github.com/microsoft/winget-pkgs/tree/master/manifests/p/Python/Python/3/13) 及 [Homebrew Python 3.13](https://formulae.brew.sh/formula/python@3.13)

首次使用缺少的 Runtime, 套件或 browser 時, 先列出來源, 版本, 安裝範圍及用途並詢問安裝, 已明確授權的安裝依當次範圍繼續. Browser 安裝依當下 `playwright-cli install-browser --help` 選擇, 已有相符 Chrome / Edge 時直接沿用, 使用者範圍或企業核准來源優先

## Context7

先確認 library 名稱與實際版本, 已有相同 endpoint 或 plugin 時沿用既有 provider. [Baseline bootstrap](../setup/cli.md) 已有 `--context7`, 會新增 `https://mcp.context7.com/mcp`, 也可獨立註冊, 不需要 Python wheel bundle:

```text
codex mcp add context7 --url https://mcp.context7.com/mcp
codex mcp list
```

`/mcp` 可使用匿名額度. 需要 OAuth 時改用官方的 OAuth endpoint, 備份並檢查既有同名設定後再執行:

```text
codex mcp add context7 --url https://mcp.context7.com/mcp/oauth
codex mcp login context7
```

API key 接法使用本機環境變數與 `bearer_token_env_var`, 不把 key 放進命令列或可發布設定. 官方 `npx ctx7 setup --codex` 與 plugin 安裝也可用, setup 會修改 config / AGENTS.md, 選用時先核對本 repo 管理的 global 指示並保留備份

已有官方 `ctx7` CLI 時可先查 `ctx7 --help`, 使用 `ctx7 library <name> <query>` 取得 library ID, 再以 `ctx7 docs <library-id> <query> --json` 查公開文件. [官方 CLI](https://github.com/upstash/context7/blob/master/packages/cli/README.md) 支援 CLI + Skills 與 MCP, 一般查詢不需要執行 `setup`, 切換模式前先核對設定寫入, 登入需求與部署限制

重新載入 Codex 後, 以公開 library 名稱測試 `resolve-library-id`, 再用回傳的 library ID 與已確認版本呼叫 `query-docs`, 核對文件來源及版本相容性. 外部查詢只帶公開技術問題, 公司程式碼與內部文件留在核准環境

官方依據: [Codex 接法](https://context7.com/docs/clients/codex), [OAuth / MCP clients](https://context7.com/docs/resources/all-clients), [Codex MCP 欄位](https://learn.chatgpt.com/docs/extend/mcp?surface=cli)

## Playwright

CLI 與 MCP 需要 Node.js 18+. 先沿用已安裝的 Playwright Skill 與專案測試, 需要補 CLI 時安裝官方套件. 下例固定已核對的版本, 換版前核對來源與目前環境:

```text
node --version
npm --version
npm install -g @playwright/cli@0.1.22
playwright-cli --help
```

公司 Windows 若需要使用者範圍的安裝位置, 可指定 prefix, 再把該目錄加入使用者 PATH, macOS / Linux 指定 prefix 時將其 `bin/` 加入 PATH:

```powershell
npm.cmd install -g --prefix "$env:LOCALAPPDATA\codex-setup\tools\npm" @playwright/cli@0.1.22
```

本 repo 提供 [Playwright CLI Skill](../../skills/playwright-cli/SKILL.md) 與 [操作參考](../../skills/playwright-cli/references/commands.md), 依既有單向 Skill 同步方式安裝至目標 client. 若選官方 Skill generator, 先查 `playwright-cli --help install`: 此次核對版本的 `install --skills` 預設寫入 `.claude/skills`, `install --skills=agents` 寫入 `.agents/skills`, `--global` 改成 home 範圍. 先核對既有 Skill ownership 與 client discovery, 避免 generator 覆寫本 repo 管理的版本

操作驗證使用已確認的 local dev URL 與必要流程, 每次呼叫都帶同一個唯一 `-s=<name>` 並保持工作目錄一致. 先 snapshot 並讀取內容, 操作後重新 snapshot, 使用目前 help 所列的 `console`, `requests` 與 screenshot 核對結果, 結束時只關閉自己的 session. CLI 的 cookies / storage 可跨呼叫保留, 關閉 browser 後預設不保留 profile, 需要跨 restart 保存登入時另選專用測試 profile

需要 MCP 互動時, 在備份並檢查既有註冊後選用:

```text
codex mcp add playwright -- npx -y @playwright/mcp@0.0.83 --isolated
```

`--isolated` 將 browser profile 留在記憶體, 不沿用日常瀏覽器的登入狀態. MCP 註冊後重新載入 Codex, 確認 browser tools 可呼叫並實際操作頁面, package 安裝與設定解析只能證明安裝狀態, UI 驗收仍須執行實際流程

官方依據: [Playwright CLI + Skills](https://github.com/microsoft/playwright-cli), [Playwright MCP 與 isolated profile](https://github.com/microsoft/playwright-mcp)

## RTK

先把 shell output 限定到必要範圍, 同一任務的 test / build / git 輸出仍過多時才試 RTK. Windows 與 macOS 可用官方列出的套件來源, Linux 使用 [官方 Releases](https://github.com/rtk-ai/rtk/releases) 的對應 binary, 或已可用的 Cargo 從官方 repo 安裝:

```powershell
winget install --id rtk-ai.rtk --exact --source winget --scope user
```

```sh
brew install rtk
# 已有 Cargo 時也可用此跨平台接法
cargo install --git https://github.com/rtk-ai/rtk
```

初期明確呼叫 CLI, 保留原始輸出與 exit code 作比較:

```text
rtk --version
rtk git status
rtk gain
```

驗證至少涵蓋成功與失敗指令, 重要 warning, 錯誤位置及 exit code, 漏掉判斷所需資料時回查原始指令. `rtk gain` 提供輸出估算, 效益另用同一任務的結果, 重試次數與 Codex 總用量評估, 輸出壓縮率不直接換算為帳單節省

初期使用明確 prefix, 要全面自動改寫時才選 `rtk init -g --codex`, 先核對安裝版本與 Codex hooks 支援, 備份並合併 config / AGENTS.md, 避免覆寫本 repo 管理的指示. Telemetry 依公司規則設定, 可用 `rtk telemetry status` 檢查

官方依據: [RTK 安裝, 指令與 Codex 接法](https://github.com/rtk-ai/rtk)

## Context 與工作台

以下接法供符合平台與需求的環境獨立選用, 每次先確認原生功能的具體不足, 以一個實際任務驗證導入成本及效果

| 工具 | 安裝與接入 | 驗證重點 |
| --- | --- | --- |
| RepoPrompt CE | 使用[官方 Homebrew tap 或 source-build 流程](https://github.com/repoprompt/repoprompt-ce)建立 Mac 本機 app, 連接核准的 repository 與 MCP client | 選取檔案, context 預覽與 Git diff 是否足夠且沒有夾帶其他專案資料, 輸出可先人工檢查 |
| cmux | Mac 執行 `brew tap manaflow-ai/cmux`, 再 `brew install --cask cmux`, 或安裝[官方 DMG](https://github.com/manaflow-ai/cmux) | 不同目錄與 CLI session 能否辨識, 通知是否可靠, 原有終端設定是否保留 |
| T3 Code | Windows: `winget install --id T3Tools.T3Code --exact`, macOS: `brew install --cask t3-code`, Linux 從[官方 Releases](https://github.com/pingdotgg/t3code/releases)選對應套件, 再連接已安裝並登入的 Codex CLI | Thread 恢復, 分工狀態, provider 切換時的 context, 權限與 worktree 行為, 採用前核對 stable / nightly channel |
| Conductor | 使用 [Homebrew cask](https://formulae.brew.sh/cask/conductor) 或[官方下載入口](https://www.conductor.build/)安裝 Mac Desktop, 依[Codex worktree guide](https://www.conductor.build/docs/guides/git-worktrees/run-codex-with-git-worktrees)建立 workspace 並執行 Codex | Base branch, 獨立工作目錄, 必要的 setup / run script, 未提交變更, diff / review 與衝突處理 |

T3 Code 的 [Orchestrator V2 nightly 0.0.46-nightly.20261003.2610](https://github.com/pingdotgg/t3code/releases/tag/v0.0.46-nightly.20261003.2610) 是已核對的預覽版來源, 需要該功能時先驗證指定版本的穩定性及資料相容性, 再決定採用 channel

## 公司與個人環境

- 公開 repo 保存流程與非機敏範例, 各環境獨立建立 credentials, roots, browser profiles, logs 與登入狀態, 不複製私人 config 或 session 資料
- 公司程式碼, 客戶資料, 內部文件, 私有 endpoint 與原始 logs 依公司核准範圍使用, 外部文件查詢以公開 library 名稱, 版本與 API 問題為限. Local CLI / MCP 的結果若送入 agent context, 仍需遵守該 agent 的資料外傳範圍
- 安裝前確認平台, package 來源, 版本, proxy / CA 與可寫位置, 有企業 CA 時沿用核准的設定, 保留 TLS 驗證, 不擅自變更系統層設定
- 選用工具前先核對同名設定與現有 provider, 備份並保留無關設定, 重新載入後才以實際 tool call, browser 操作或 CLI 結果確認可用

## 工具與 MCP 的生命週期

CLI 指令, browser session, MCP server 與桌面檢視器各自管理生命週期. MCP client 可為不同任務建立獨立 stdio server, 一次回覆完成時仍可能保留連線. 盤點時核對啟動時間, PID / 父 PID, 父程序是否早於子程序, client ownership, browser 子程序與監聽位置, 將 Windows launcher / venv redirector 分開計數. 有效父程序仍在只證明程序來源, 不能單靠數量判定任務是否仍需要該連線

Playwright CLI 在成功, 失敗或取消流程的結束處關閉自己的具名 session, 再以目前版本的 session list 核對. Headed session 可能持續保留, 不以 headless 的 idle timeout 取代清理. Playwright MCP 的 browser close 與 MCP server 結束是不同操作, server 由 client 管理. textlint, RTK, Local Documents, Jev 等 stdio MCP 同樣先核對 client 是否仍持有連線, 臨時建立的驗證 client / 子程序則由建立它的流程在結束時清理

本包的 Serena MCP 安裝參數包含 `--enable-web-dashboard false`, `--open-web-dashboard false` 與 `--enable-gui-log-window false`, 避免新安裝為每條連線建立系統匣圖示或視窗. 新安裝會使用這組參數, 既有註冊可從管理器的「編輯連線」更新參數, 必要的 symbol 與 references 工具仍透過 stdio 運作

若要手動使用 dashboard, 將該 MCP 的 `--enable-web-dashboard` 改為 `true`, 再採用以下 browser 設定

Serena 1.7.0 在 Windows 預設使用 `app` dashboard interface, 每個 server 各建立一個 native viewer 與 tray 圖示. `--open-web-dashboard false` 只讓 viewer 從隱藏狀態啟動, 關閉視窗則縮到 tray. 多任務環境可在該機器的 Serena global config 選擇官方的 `browser` interface 並關閉自動開啟, 保留獨立 server 與 dashboard, 按需要手動開啟網頁:

```yaml
web_dashboard: true
web_dashboard_open_on_launch: false
web_dashboard_interface: browser
```

先備份並合併這幾個欄位, 保留既有 project, language, credential 與網路設定. 新設定在下一次 Serena server 啟動時載入, 既有 viewer 仍跟隨其 server, 需要時在工作保存後重新啟動所屬 client

需要單一 tray 圖示時可在已驗證的平台選 `web_dashboard_interface: tray_manager`. Serena 1.7.0 的 manager 啟動等待約 3 秒, 本機啟動較慢時註冊可能 timeout, 先驗證共用 manager, 註冊與自動退出, 失敗時保留原因並改選 `browser`. `browser` 搭配停用自動開啟可避免 native viewer / tray 子程序, dashboard 仍可透過工具的開啟功能或已確認的 loopback URL 使用. [Serena 官方 dashboard 說明](https://oraios.github.io/serena/02-usage/060_dashboard.html)

核對為殘留時只清理已確認屬於該任務的 session / 程序, 優先使用工具的原生關閉方式. 保留有效的其他任務, 一般瀏覽器, 正在執行的測試與有意常駐的 monitor, 不以名稱相同或父 launcher 結束作為全面終止的依據
