# 用途、工作流程與更新

## 遊戲開發, 數值平衡與模擬

先以正式遊戲的規則跑一段代表性流程, 用試算表調參, 用測試檢查規則, 再依問題補統計, 公式推導與資源流工具, 適用放置遊戲, 經營, RPG 成長與其他有數值循環的遊戲

## 按需求選一項

| 選項 | 類型 | 適合處理的問題 |
|---|---|---|
| 遊戲共用邏輯的 headless 模擬器 | 專案程式 | 不開畫面也能跑購買, 生產, 解鎖與重置, 保持正式規則一致 |
| `excel`, `google-sheets` | 既有 MCP / connector 接法 | 成本, 產量, 解鎖與成長曲線, 確認公式真的重算再讀結果 |
| `numpy` | Python library | 抽樣, 隨機分布與大量陣列計算 |
| `pandas` | Python library | 整理不同策略, 參數與模擬結果 |
| `scipy` | Python library | 信賴區間, 統計與有條件的參數最佳化 |
| `sympy` | Python library | 等比成本, 期望值與方程推導, 本機使用免 API key |
| `matplotlib`, 既有 `echarts` | Python library / 本機圖表 MCP | 成長曲線, 分布, 瓶頸與參數比較 |
| `fast-check` | JS / TS 專案測試 library | 自動產生操作序列與邊界值, 縮小失敗案例 |
| `hypothesis` | Python 專案測試 library | Python 規則與狀態機測試, 沿用專案測試 runner |
| `machinations` | 雲端設計與模擬產品 | 用來源, 儲存, 消耗與轉換節點梳理資源循環 |
| `wolfram` | 既有官方 Local / Cloud MCP 接法 | 複雜公式驗算與單次計算 |
| `jupyter` | 既有 Notebook MCP 接法 | 保存實驗參數, 程式, 圖表與結果 |
| `simpy` | Python library | 排隊, 建造完成與資源爭用的離散事件模型 |
| `optuna` | Python library | 大量參數搜尋與多目標實驗, 已有明確評估函數後選用 |

Machinations 免費 Community 模型預設公開, 私有設計依現有帳戶方案選用, 未確認可直接註冊的官方 MCP endpoint, 清單提供產品入口. Wolfram 沿用既有接法, Cloud 與 Local 的能力, 執行範圍與授權分開核對

SimPy 與 Optuna 是進階候選, 正式遊戲已有事件與排程邏輯時優先呼叫原實作, 額外模型需先用代表性軌跡對照, 避免兩份規則逐漸不同

## Windows 與 macOS 的入口

Windows 執行 `launch-cli.cmd mcp --profile game`, macOS / Linux 執行 `sh launch-cli.sh mcp --profile game`, 選單包含遊戲分類與既有計算, 試算表, 圖表及驗證接法, 每次選一項

Python 與 JS library 需先選目標專案, 所以入口列出該項相依與專案安裝步驟, 不安裝到全域或自行新增 MCP. 官方 API / 帳戶服務仍各自授權, Codex 側邊欄內建整合沿用原本設定

新 Python 模擬專案可在自己的目錄建立獨立環境, NumPy 與 SciPy 的設定清單中的版本需要 Python 3.12+, 其他項目的相容條件見 [相依清單](../../mcp/tools/development-tools.requirements.json)

```text
py -3.13 -m venv .venv-balance
.venv-balance\Scripts\python.exe -m pip install --only-binary=:all: -r <setup-root>\tools\game-requirements\numpy.txt
.venv-balance\Scripts\python.exe -m pip check
```

```sh
python3.13 -m venv .venv-balance
.venv-balance/bin/python -m pip install --only-binary=:all: -r <setup-root>/mcp/tools/game-requirements/numpy.txt
.venv-balance/bin/python -m pip check
```

`<setup-root>` 替換為已核對的 checkout 或 setup wheel 內資源位置, 各 `*.txt` 只指定一項頂層套件, 其必要相依由 pip 解析. 既有專案優先使用自己的 Python / package manager / lockfile, 不照範例另建第二份環境或覆寫已鎖版本

fast-check 由 JS / TS 專案的 package manager 加為 devDependency, 使用對應的 `add -D` 或 `install --save-dev`, 版本與 lockfile 保存在該專案, 不裝成全域 CLI

## Wheel 與更新

Setup wheel 收納分類, 相依說明, 單項 requirements 與這份文件. 科學計算套件保留官方 wheel, NumPy, SciPy 等需符合 OS, CPU, Python 與 ABI, 不將 Windows 執行檔當成 macOS 通用包

需要離線使用時, 在相符環境以 `python -m pip download --only-binary=:all: -r <selected-requirements> --dest <local-wheel-cache>` 準備該項及必要相依, 保存 hash 與授權資料, 再以 `--no-index --find-links <local-wheel-cache>` 安裝, cache 與 venv 不提交到 Git

Requirements 是新環境的已核對起點, 遊戲採用後以自己的 lockfile 維護. 更新先預覽候選版本及 runtime 條件, 在該專案環境更新並重跑規則, 存讀檔與代表性模擬, 保留原版本與基準結果, `codex-tool-update` 維護 setup 管理的工具, 專案 library 使用其原本更新流程

## 使用 Skill 與 Agent

[Game Balance Simulation](../../skills/game-balance-simulation/SKILL.md) 依實際專案執行假設, 基準, 模擬, 比較與重播, 按需求選工具, 不綁 TypeScript, Python 或特定引擎

Main 保留玩法, 規則與採用決策, 實作 owner 維護共用核心與實驗. 有獨立審查需求時可選 [唯讀角色範本](../../skills/agent-governance/assets/project-starter/root/.codex/agents/game_balance_reviewer.toml), 不將範本視為已啟用角色

實驗範例, 報告欄位與研究來源見 [Playbook 遊戲數值教學](https://github.com/gaze9999/codex-playbook/blob/main/game-balance.md)

## UI / UX 工具與流程

工具依用途分類, 設計與開發電腦可用 `--profile design` 或 `--profile development` 篩選選單. 類別只決定顯示範圍, 每次仍選一項, 不會安裝整組

| 工具 | 包內接法 | 相依與用途 |
| --- | --- | --- |
| [Mobbin](https://github.com/mobbin/mobbin-mcp-server) | 官方 hosted MCP, `mobbin`, OAuth | Pro / Team 帳戶, 搜尋實際產品畫面與流程, 註冊後仍需登入及權限驗證 |
| [Baymard](https://baymard.com/blog) | `baymard` 研究來源入口 | 讀免費研究文章, Premium 內容依既有帳戶, 未確認官方 MCP endpoint |
| [Penpot](https://penpot.app/ai/mcp-server) | `penpot`, 官方 hosted / local MCP 設定入口 | 帳戶, 私有 MCP key 與連接中的設計檔, 本機模式另需相符版本的 Node server 與 plugin |
| [Angular Material / CDK](https://material.angular.dev/) | `angular-material`, library 入口, 沿用 `angular` 或版本文件查詢 | 依實際 Angular workspace 選版, 選取入口不安裝 UI library 到專案 |
| [spartan](https://www.spartan.ng/documentation/mcp) | `spartan`, 官方 `@spartan-ng/mcp` 1.5.0 | 此 preset 使用 Node 22+ / npm, 查元件, blocks 與 API, 使用前選與專案相符的文件 cache 版本 |
| [Axe MCP Server](https://docs.deque.com/devtools-server/4.0.0/en/axe-mcp-server/) | `axe`, 官方 npm / Docker 設定入口 | 需啟用 MCP 的 Deque 訂閱, API key 或 OAuth, npm 模式另需 Node 22.19+ 與 Chromium |

Mobbin 使用 `https://api.mobbin.com/mcp`, 選定後由既有入口註冊, 再依 client 的 OAuth 流程登入. 安裝器不購買訂閱, 不從 endpoint 已存在推論帳戶可用

Penpot hosted 模式從既有帳戶啟用 MCP, 選定設計檔並使用其提供的私有設定, key 留在受保護的本機設定. [官方 local server](https://github.com/penpot/penpot/tree/develop/mcp) 使用與 Penpot 相符的 `@penpot/mcp` 版本, 預設連至 `http://localhost:4401/mcp`, 同時啟動 plugin server, 保持 browser/plugin 連接. 本機套件版本與 hosted Penpot 版本分開核對, 不用 registry latest 自動升級兩者

Axe 免費 browser extension 與需訂閱的 Axe MCP Server 分開選用. 依 [官方 authentication](https://docs.deque.com/devtools-server/4.0.0/en/authentication) 設定單一憑證模式, OAuth 使用官方 supervisor 更新短效 token. 掃描前確認所用 Deque instance 與頁面資料範圍. 既有測試 runner 也可使用 [axe-core / Playwright](https://playwright.dev/docs/accessibility-testing) 做本機自動檢查, 不因採用 axe 就要求付費 MCP

## 從需求到驗證

先選一段代表流程, 明確列出使用者目的, 入口, 成功, 空狀態及可恢復的錯誤. 研究真實產品畫面與研究文章時保留原始連結, 日期, 適用場景及證據類型, 複製畫面不是目標流程已可用的證明

原型與實作沿用已選設計系統, 依功能需求比較 form, table, dialog, keyboard / focus, responsive 與 localization 支援. 從一個小區塊驗證資訊階層, 文案與互動, 有實際問題再擴大. 元件使用量, stars 或設計工具主流程度不能代替相容性與授權核對

驗證使用已核准的測試資料與頁面, 檢查實際任務流程, keyboard / focus, responsive, 更新與空狀態, 再加可重複的自動無障礙掃描. 文案依可用校對能力及語言分段處理, lint 通過與語意, 資料正確性及完整無障礙分開判斷

[spartan 維護者與使用者的 MCP 討論](https://github.com/spartan-ng/spartan/discussions/819) 可用來理解整合需求, 目前能力以官方 MCP 文件及實際 package 為準. 個人使用心得只作場景線索, 不轉成未量測的成效數字

## 元件授權

[PrimeUI 公告](https://primeui.dev/nextchapter) 指定新授權模式從 PrimeNG 22, PrimeReact 11, PrimeVue 5 開始, 既有 MIT release 的權利保留. Community 有資格與續期條件, 導入時核對所選版本及組織資格, 不將所有商業專案一概判定為免費或付費. `primeui` 入口保存官方授權參考, 不在這裡複製會變動的方案價格

## 分類與工具更新

安裝器與完整接法收在 `codex-tool-setup` wheel, Python MCP 另有獨立 server wheel. Node 工具, hosted MCP, 原生 App, library 與網站來源保留原本接法及相依, 不把 recipe wheel 說成它們的執行檔

| Profile | 適合的電腦 / 工作 | 選單範圍 |
| --- | --- | --- |
| `development` | 開發電腦 | 開發, 遊戲模擬, UI / UX, 文件校對, 辦公, 視覺化與計算 |
| `design` | 設計與原型 | UI / UX, 視覺化與文字校對 |
| `game` | 遊戲開發與數值實驗 | 遊戲套件, 試算表, 公式, 圖表與選定的開發驗證工具 |
| `office` | 文件與辦公 | Office / 文件, 校對, 帳戶服務 |
| `research` | 搜尋與研究 | 搜尋收集, 計算, 醫療原始來源與校對 |
| `personal` | 生活與學習 | 生活帳戶, 天氣交通, 學習遊戲, 購物財務 |
| `all` | 查看完整清單 | 全部分類 |

Profile 是選單篩選, 各工具仍獨立安裝, credentials 與設定也各自保存, `game` 依分類加上明確相關項目, 不將其他生活或金融來源一併列入. 公司機器只選工作需要且符合資料邊界的工具, 不因 profile 包含帳戶服務就啟用私人帳戶或擴張外傳範圍

Windows 使用 `launch-cli.cmd mcp --profile development`, macOS / Linux 使用 `sh launch-cli.sh mcp --profile development`, 再選類別與單一工具, `--list --profile development` 只列清單, 安裝 wheel 後使用 `codex-mcp-setup --profile development`, Python 不足時沿用個別工具入口的首次安裝詢問

## 自動檢查與單項更新

`codex-tool-update --tool <tool>` 自動查官方更新通道, 顯示目前 / 新版, runtime 條件, shared package 影響及更新步驟. 只有加 `--apply` 才更新, 已明確授權的無人值守執行可加 `--yes`. 同一入口可重跑, 沒有新版便不安裝, 不降版, 不新增未安裝工具

Desktop 與獨立 CLI 的 user prefix 可能不同, 預設位置未找到套件時, updater 會從該工具已註冊的 MCP entry 核對使用者目錄內的 setup 管理位置. 自訂位置使用 `--npm-prefix <absolute-path>`, 不從任意 MCP 路徑改動其他專案的套件

```text
codex-tool-update --tool spartan
codex-tool-update --tool spartan --apply
codex-tool-update --tool spartan --apply --yes
```

Repository 入口為 `python mcp/scripts/update_development_tool.py --tool <tool>`, 或在原安裝入口加 `--update`, 例如 `launch-cli.cmd mcp rtk --update --apply`. macOS 同樣可用 shell 入口. 指定 `--interface mcp` 只選該工具的 MCP package, 不順便切換 provider 或登入

| 類型 | 更新方式 |
| --- | --- |
| Setup user prefix 中的 npm 工具 | 查 npm `latest` stable, 安裝預覽中的明確版本, `engine-strict` 核對 runtime, 共用 package 的其他工具會列出 |
| Setup 管理的獨立 Python MCP | 查 PyPI stable, 使用該工具原有 venv 的 pip, 由 pip 核對 Python 相容性 |
| RTK native | 查官方 stable release, 選相符 OS / CPU asset 並核對 SHA-256, 安裝到 setup user prefix, 保留原 package-manager 安裝. 只調整符合原 executable 的 setup adapter, roots 與其他設定保留 |
| Setup wheel / catalog | 在安裝此 wheel 的獨立 venv 執行 `codex-tool-update --tool setup --apply`, 查官方 release manifest, 核對 wheel checksum, 更新同一 venv |
| Hosted MCP | 由服務商維護 server, client reload 後仍需核對實際工具, 帳戶, 權限與 quota |
| Plugin, App, project library 或 manual setup | 沿用各自更新通道, Penpot 與 Angular 等需先核對目標版本, 不以全域 latest 覆寫專案或內建 runtime |

[遊戲開發接法](workflows.md) 將 Python 計算與 JS / TS 測試套件放在目標專案, 使用自己的 lockfile, 單項 requirements 與相符平台的 wheel, 更新後對照原模擬基準

更新紀錄保存預覽的來源與原版本, RTK executable 與設定變更使用既有 backup 機制. Package 安裝失敗可能已改動相依, 依保留紀錄核對及恢復, 不宣稱只還原主套件就等同完整環境 rollback. 更新工具不改語言詞表, 權限, 帳戶或 Model 設定

要持續自動更新時, 將已選定且已授權的單項更新命令交給現有排程工具, 本安裝包不自行新增背景服務或排程. 新通道無法查證, 網路失敗或不相容時回報具體原因, 不以查詢失敗當作已最新. 更新完成仍需 client reload 及實際工具呼叫驗證
