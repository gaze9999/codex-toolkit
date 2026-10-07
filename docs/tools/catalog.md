# 按需求選用 MCP 與資料來源

本工具包提供開發, 生活, 研究, 圖表及領域來源的整合接法. [相依清單](../../mcp/tools/development-tools.requirements.json) 保存每項工具的平台, 來源, Runtime / 套件, credential 環境變數名稱與安裝設定

`kind` 區分 MCP, 開發工具, connector, Skill, API 與網站. `origin` 區分官方, 社群, 維護團隊及本 setup adapter. 清單包含可自動安裝 / 註冊的項目, 也包含需先選定帳戶, app, project 或檔案範圍的候選, `manual_setup_required` 會列出該項的具體步驟, installer 會保留設定並停止

## 使用前確認

相同任務已有相容 CLI 時, 優先沿用 CLI 與所屬 Skill, 需要特定能力, 用戶端存取或結構化防護時再使用 MCP / connector, 詳細條件見 [CLI / MCP 選用](selection.md). 清單與 requirements 保存支援的設定方式, 本輪可呼叫工具仍須依實際 discovery 核對

Codex 可先查 `codex mcp list --help`, 再用 `codex mcp list` 或已支援的 JSON 輸出盤點設定. 區分已設定 / 啟用, 本輪已載入, 認證狀態與實際呼叫結果, CLI 註冊清單也可能與 Desktop / plugin 提供的工具不同. 診斷輸出只保留需要的欄位, 不公開 env, header 或 credential 值, 官方設定方式見 [OpenAI MCP 文件](https://learn.chatgpt.com/docs/extend/mcp?surface=cli)

只啟用當次需要的能力, Workspace Inspection 尚未設定 roots 或工具尚未載入時, 沿用已授權的 CLI 檢查. Serena 需核對目標語言, 索引與實際工具, Spartan 需符合目標 Angular 專案. Browser, 文件寫入及帳戶操作各自保留資料範圍與驗證條件, 不因清單有工具就安裝, 登入, 擴大 roots 或呼叫付費 API 探測

## 獨立操作

Windows 可直接執行 [launch-cli.cmd mcp](../../launch-cli.cmd), 或在 CMD 輸入下列指令. 選擇類別與工具後, 引導會列出相依與安裝範圍, 沿用既有安裝, 並協助連接需要 OAuth 的帳戶

CMD 入口使用 Windows 內建 PowerShell, 該次程序採用 RemoteSigned, 公司群組原則依 [PowerShell 執行原則的優先順序](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_execution_policies?view=powershell-5.1)套用

```cmd
launch-cli.cmd mcp
launch-cli.cmd mcp notion
launch-cli.cmd mcp playwright
```

macOS / Linux 在終端機執行:

```sh
sh launch-cli.sh mcp
sh launch-cli.sh mcp notion
```

Home Assistant 與 RSS 會提示輸入 endpoint 或 feeds 路徑, key 的提示只顯示環境變數名稱. 選到 manual setup 的工具會顯示必要步驟與文件, 不先安裝整批相依. 無法互動的 agent / CI 保留以下 Python 預覽入口, `--list` 列出可選名稱, `--guided` 使用同一套引導流程, `--login` 可在已選 OAuth service 的安裝完成後明確啟動登入

缺少 Python 時, Windows 選單仍可先選工具, macOS / Linux 會先詢問工具名稱. 選定項目後才確認 Python bootstrap, 再顯示該工具自己的安裝清單. 安裝後若仍有缺項會列出原因並停止登入, 已存在的 MCP 以實際 entry 名稱登入, connector 沿用原本的帳戶連接流程

以下每一行選一項, 預設只檢查或預覽:

```text
python mcp/scripts/check_development_tools.py --tool playwright --interface mcp
python mcp/scripts/install_development_tool.py --tool playwright --interface mcp
python mcp/scripts/install_development_tool.py --tool rtk --interface mcp
python mcp/scripts/install_development_tool.py --tool tavily
python mcp/scripts/install_development_tool.py --tool exa
python mcp/scripts/install_development_tool.py --tool notion
python mcp/scripts/install_development_tool.py --tool echarts
python mcp/scripts/install_development_tool.py --tool arxiv
```

選定工具後用 `--apply` 確認該清單的來源, 版本, 安裝範圍及用途, 已授權同一範圍可加 `--yes`. Windows [CMD 入口](../../launch-cli.cmd) 支援工具名稱, `-Interface mcp` 及 `-Python`, macOS / Linux [入口](../../launch-cli.sh) 支援同一組 Python installer 參數. 缺少 Python 時先預覽並詢問 bootstrap, 每次只處理該工具及必要相依. 平台不支援或 manual setup 尚未完成時停止

Hosted MCP 的註冊與 OAuth 是不同步驟. 登入使用 `codex mcp login <實際 entry 名稱>`, 或該服務正式支援的 connector 流程. Key 只保存環境變數名稱, 使用 `bearer_token_env_var`, `env_http_headers` 或 stdio `env_vars`, 不保存 secret 本文或帶 key 的 URL. 設定備份與 readback 完成後, 在重新載入的 client 核對 tools/list 及安全的實際呼叫. 這些欄位依 [Codex 官方設定](https://learn.chatgpt.com/docs/config-file/config-reference)

已啟用且相容的 plugin / connector 優先沿用, 檢查器辨識到既有 provider 時保留它, 還需確認帳戶授權及實際操作. 個人與公司電腦分別建立 credentials, log roots, browser profile 及 session, local MCP 的結果送入 agent context 時仍須遵守該環境的外傳邊界

## 開發工具

先依 [CLI / MCP 選用指引](selection.md) 核對任務與 client 能力, 不以是否有狀態作為唯一判準. CLI / Desktop 安裝見 [development-tools.md](development.md), 加 `--interface mcp` 選擇下列接法

| 工具 | MCP 接法與相依 | 驗收與限制 |
| --- | --- | --- |
| [Context7](https://context7.com/docs/clients/codex) | 官方 hosted MCP, 既有 entry 可沿用 | 公開 library resolution / docs query, 核對實際版本 |
| [Playwright](https://github.com/microsoft/playwright-mcp) | 官方 `@playwright/mcp@0.0.83`, Node 18+ / npm, 以絕對 Node entry 註冊 | 隔離 headless Chrome profile, 需已安裝 Chrome, 與 CLI / Skill 可並存 |
| [Chrome DevTools](https://github.com/ChromeDevTools/chrome-devtools-mcp) | 官方 1.10.1, 相容 Node / npm, 以絕對 entry 註冊 | 隔離 headless Chrome, trace / network / console, 此 preset 關閉 usage statistics 與 CrUX lookup |
| [Edge DevTools](https://learn.microsoft.com/en-us/microsoft-edge/web-platform/devtools-mcp-server) | `edge-devtools`, 獨立 Python wheel 內含官方 DevTools MCP 1.10.1, 需相容 Node 與已安裝 Edge | Codex 的 `edge_devtools` entry, 隔離 headless Edge, DOM / console / network / trace, 關閉 usage statistics 與 CrUX lookup |
| [Serena](https://github.com/oraios/serena) | Maintainer PyPI `serena-agent==1.7.0`, Python 3.11+ 的獨立 venv | 使用前明確啟用目標 repository, 依專案語言核對 language server, 查 symbol 與 references |
| [RTK](https://github.com/rtk-ai/rtk) | 官方 CLI 0.50+ 加本 setup 的 Python adapter, `mcp==2.2.0`, 獨立 venv | `rtk pipe` 過濾既有文字, 保留原始 exit code, 改動 diagnostics 時回傳原文, 檔案預設無 read roots |
| [RepoPrompt CE](https://github.com/repoprompt/repoprompt-ce) | 原生 Mac app 的 `repoprompt-mcp` / `rpce-cli`, 可指定 `--mcp-executable` | Windows 保留接法, native app 與 source build 的 macOS 需求分開核對 |
| [cmux](https://cmux.com/docs/api) | 已有 macOS cmux CLI 加本 setup 的 Python adapter, 各自 venv | inspect workspace/panel, 建立 workspace/split 與 focus, 保留 cmux socket access policy, 需從核准 cmux session 啟動 |
| [T3 Code](https://github.com/pingdotgg/t3code) | App 管理的 `/mcp` session / token 接法, 先核對已安裝 release | Main source 的 session 支援需對照 release, 未確認可供外部 client 持久使用的 credential bootstrap, 保留 manual setup |
| [Conductor](https://www.conductor.build/docs/api/mcp) | 官方 hosted `https://api.conductor.build/mcp`, OAuth, Cloud workspace Beta | Cloud 與 Mac Desktop 是不同接法, 需組織權限與選定 workspace |

Serena 的可攜偏好保存於 [preferences.yml](../../mcp/tools/serena/preferences.yml), 使用瀏覽器介面並關閉啟動時自動開啟視窗, 欄位已核對 `serena-agent==1.7.0` 與 [官方 Dashboard 說明](https://oraios.github.io/serena/02-usage/060_dashboard.html). 這是設定片段, 套用前備份既有 `serena_config.yml`, 再合併這兩個欄位, 保留原有 `projects`, 本機路徑與其他設定. Installer 不會自動寫入這份片段, MCP 啟動參數仍優先, 本 setup 的註冊預設以 `--enable-web-dashboard false` 關閉 Dashboard, 只有明確啟用後才使用介面偏好

RTK log read roots 明確選定, 例如 `--read-root /approved/project`, 只接受該範圍內 UTF-8 `.log`, `.txt`, `.out`, 單份上限 1 MB. 輸出壓縮率與帳單節省分開量測. Adapter 不執行 project command, cmux adapter 不提供任意 terminal text 或關閉 / 刪除操作

## UI / UX

`mobbin` 提供官方 hosted MCP 的獨立註冊與 OAuth 流程, 需 Pro / Team 帳戶, `spartan` 提供官方 Node MCP 的單項安裝, `penpot` 與 `axe` 保存官方 MCP 的帳戶 / 環境設定入口, 完成該項相依後再驗證實際操作

`baymard`, `angular-material` 與 `primeui` 分別提供研究, library 與授權參考入口, 不將它們宣稱為新增 MCP server. 接法, 版本相容性與驗證方式見 [UI / UX 工具與流程](workflows.md), 電腦用途分類及單項更新見 [工具更新](workflows.md)

## 文字校對

`textlint` 提供繁中台灣詞表與半形標點 MCP, `textlint-ja` 提供保留日文標點的獨立 MCP, `cspell` 使用 CLI 檢查英文拼字與專案術語, 需要英文文法檢查時再選 `languagetool`, 各項獨立安裝與設定. 詳細用途及規則見 [中英日文字校對](proofreading.md)

## 遊戲開發與模擬

`--profile game` 提供遊戲專案套件與既有 Excel / Sheets, Wolfram, Jupyter, 圖表及驗證接法, 科學計算與 property-based testing 依目標專案安裝, Machinations 提供產品入口, 詳見 [遊戲開發接法](workflows.md), 各項的 MCP, library 與帳戶條件分開標示

## 生活與帳戶

| 選項 | 接法 | 首次使用要確認 |
| --- | --- | --- |
| `todoist` | [官方 hosted MCP](https://developer.todoist.com/), OAuth | 待辦帳戶, project / 分類與寫入權限 |
| `readwise` | [官方 MCP](https://docs.readwise.io/tools/mcp), `https://mcp2.readwise.io/mcp`, OAuth | Reader / highlights 與有效服務訂閱, 舊端點已 deprecated |
| `raindrop` | [官方 MCP Beta](https://developer.raindrop.io/mcp/mcp), OAuth | Pro 帳戶與 collections |
| `notion` | [官方 MCP](https://developers.notion.com/guides/mcp/get-started-with-mcp), OAuth | 選定 workspace / 頁面範圍, 沿用可用的 Notion Skills |
| `dropbox` | [官方 MCP Beta](https://help.dropbox.com/integrations/connect-dropbox-mcp-server), OAuth 或既有 plugin | 帳戶及指定 files / Paper 文件 |
| `google-calendar`, `google-drive`, `google-docs`, `google-sheets` | 優先已可用 App / connector, [官方 Workspace MCP](https://developers.google.com/workspace/guides/configure-mcp-servers) 為 Developer Preview | Preview enrollment, Google Cloud OAuth client / scopes, 開發者設定完成前保留 manual setup |
| `google-maps` | [官方 Grounding Lite](https://developers.google.com/maps/ai/grounding-lite), `https://mapstools.googleapis.com/mcp` | Google Cloud billing / API enabled, `X-Goog-Api-Key` 從 `GOOGLE_MAPS_API_KEY` 讀取 |
| `home-assistant` | [官方 integration](https://www.home-assistant.io/integrations/mcp_server), 使用自有 instance 的 `/api/mcp` | `--server-url` 明確提供 endpoint, 可用 `--token-env-var`, 先設定 exposed entities 與 control 權限 |
| `github` | 既有 plugin / connector 的 account setup | 核對實際 provider, 帳戶與 repository 權限 |

## 搜尋與持續收集

| 選項 | 接法 / 相依 | 用途與驗收 |
| --- | --- | --- |
| `tavily` | [官方 keyless MCP](https://docs.tavily.com/documentation/keyless), HTTP header `X-Tavily-Access-Mode: keyless` | 限流 Search / Extract, 未帶此 header 會要求登入 |
| `exa` | [官方 MCP](https://exa.ai/docs/get-started/exa-mcp), keyless limited | 搜尋 / fetch, account agent runs 與更高額度另選授權模式 |
| `brave-search` | [官方 Node MCP](https://github.com/brave/brave-search-mcp-server) 2.1.4, Node 22+ / npm, `BRAVE_API_KEY` | 網頁 / 新聞 / 在地資料, 依帳戶 quota |
| `firecrawl` | [官方 keyless endpoint](https://docs.firecrawl.dev/mcp-server/keyless) `https://mcp.firecrawl.dev/v2/mcp` | 限流 Search / Scrape / Parse, `--token-env-var FIRECRAWL_API_KEY` 為帳戶模式 |
| `rss` | [社群 RSS Aggregator](https://github.com/imprvhub/mcp-rss-aggregator) 0.3.0 pinned commit, Node 20+ / npm / Git | `--feeds-path` 指定已存在 OPML / JSON, Python installer 建立獨立 source checkout 並 build |
| `x` | [官方 X MCP](https://docs.x.com/tools/mcp), app-only Bearer 從 `X_APP_BEARER_TOKEN` 讀取 | 按量 API, 此 preset 為 app-only read route, user context / bookmarks / 發布需另選 xurl OAuth bridge |
| `reddit` | [社群 RSS MCP](https://github.com/jorgen-k/reddit-mcp), Python, `reddit-rss-mcp==1.2.1`, 獨立 venv | PyPI 名稱需核對, `reddit-mcp` 是另一個 project, 沒有 scores 或完整留言樹 |
| `apify` | [官方 hosted MCP](https://docs.apify.com/integrations/mcp), OAuth | 大量結構化收集前選 Actor, 核對費用, 可靠性與資料範圍 |
| `openalex` | [官方 MCP](https://help.openalex.org/access/connector/), OAuth | 研究脈絡, 文獻 / 作者 / 引用 metadata 與全文位置 |
| `arxiv` | [社群 arXiv MCP](https://github.com/blazickjp/arxiv-mcp-server), Python 3.11+, PyPI 0.8.0, 獨立 venv | MCP SDK 1.x 與本 setup adapter 分開, PDF / pro extras 另選, 保存文獻與預印本 / 正式版本資訊 |

先選 Tavily 或 Exa 處理搜尋缺口. 固定來源再加入 RSS, 食記保留多篇原文的日期, 價格與業配資訊, 回店家頁核對營業資訊. MCP 提供取資料能力, 排程, 累積紀錄, 去重與週報依獨立工作流的實際授權及狀態設定

## 天氣與交通

| 選項 | 來源 / 相依 | 範圍 |
| --- | --- | --- |
| `cwa-weather` | [GoneTone 社群 MCP](https://github.com/GoneTone/mcp-server-taiwan-weather), npm 0.1.4, Node / npm, `CWA_API_KEY` | 氣象署 F-C0032-001, 36 小時縣市預報 |
| `cwa-extended` | [roc-cwa 社群 MCP](https://github.com/lwsinclair/roc-cwa-mcp), source 0.1.0, Python 3.10+ / mcp[cli] / requests | 3 天 / 一週與雨量, 原入口把 key 當 positional argument, 啟用前需核准的 credential-safe launcher |
| `open-meteo` | [社群 Open-Meteo MCP](https://github.com/cyanheads/open-meteo-mcp-server) 0.4.0, Node 24+ / npm | 全球天氣, 空品及相關資料, 非商業 keyless, 商業用途核對 paid API |
| `tdx` | [交通部官方 MCP](https://github.com/tdxmotc/MCP), hosted rail endpoint | `cid` / `cst` headers 從 `TDX_CLIENT_ID` / `TDX_CLIENT_SECRET` 讀取, 依帳號權限 / 點數, 訂票另申請 |

## 視覺化, 設計與計算

| 選項 | 來源與接法 | 啟用前檢查 |
| --- | --- | --- |
| `echarts` | [社群 MCP ECharts](https://github.com/hustcc/mcp-echarts), Node 18+ / npm 0.7.1, 本機 renderer | `@napi-rs/canvas` 目標平台 binary, PNG / SVG / option 實測, option 中外部 URL 與 optional MinIO 要另核對 |
| `mapbox` | [官方 MCP](https://github.com/mapbox/mcp-server) | Token, API quota, 地點資料及 client 互動地圖支援 |
| `mermaid` | [官方 MCP](https://mermaid.ai/docs/ai/mcp-server), `https://mcp.mermaid.ai/mcp` | 所選功能的 account / token 與可編輯 diagram source |
| `excalidraw` | [官方 MCP App](https://github.com/excalidraw/excalidraw-mcp), `https://mcp.excalidraw.com` | Client MCP App 顯示及可編輯 drawing source |
| `wolfram` | [官方 Local / Cloud MCP](https://www.wolfram.com/artificial-intelligence/mcp/) | 選 local licensed app 或 Cloud account, 核對 Runtime / quota / 外傳輸入 |
| `jupyter` | [Datalayer Jupyter MCP](https://github.com/datalayer/jupyter-mcp-server), Python package 2.2.3 | 選定 Jupyter Server / kernel, `code-sandboxes` 相容版本, token, notebook 目錄與執行權限 |

先沿用現有 visualize, Mermaid inline 或 plotting 能力. MCP 補持續操作或特定產出缺口, 遊戲數值以可重現參數, 模擬與敏感度檢查驗證, 玩法與策略分布另以遊玩 evidence 驗收

## 文件與領域候選

以下各項都有獨立 checker / preview, manual setup 保存必要相依及具體接法, 選定環境與操作範圍後才啟用

| 選項 | 類型 / 來源 | 必要相依與選用條件 |
| --- | --- | --- |
| `excel` | 社群 [Excel MCP](https://github.com/haris-musa/excel-mcp-server) | Python 3.11+, 1.1.1, `stdio --allow-dir`, 公式結果由已確認的計算引擎取得, 優先 spreadsheets |
| `markitdown` | [Microsoft 官方 MCP package](https://github.com/microsoft/markitdown) | Python 3.10+, 0.0.1a7, format extras 與允許的 files / URLs, 優先已有 local_documents |
| `carbone` | [官方 MCP](https://github.com/carboneio/carbone-mcp) | 選 Cloud / 自架, service token, 範本, output 及 conversion engine |
| `jisho` | [社群 MCP](https://github.com/giuliocapecchi/jisho-mcp) | 選 source/runtime 及公開查詞端點, 核對讀音與詞性 |
| `anki` | [社群 MCP](https://github.com/ankimcp/anki-mcp-server) | Anki Desktop / AnkiConnect, deck 備份及修改 / 刪除權限 |
| `steam` | [社群 MCP](https://github.com/matheusslg/steam-mcp) | 選 package/runtime, Steam credentials / visibility / store region |
| `igdb` | [社群 MCP](https://github.com/bielacki/igdb-mcp-server) | 選 package/runtime, Twitch developer app / IGDB token / quota |
| `sensor-tower` | [官方 MCP](https://sensortower.com/mcp-server-demo) | API 訂閱及正式 onboarding 設定, 市場 / 營收資料為估算 |
| `taiwan-price-compare` | [社群 MCP](https://github.com/coseto6125/mcp-taiwan-price-compare) | 選 Python source/runtime, 回商品頁確認型號, 運費, 活動與日期 |
| `taiwan-card-rewards` | [社群 MCP](https://github.com/acetaxxxx/taiwan-card-rewards-mcp) | 先輸入有日期的銀行回饋規則與上限, 回饋容量及可刷額度分開保存 |
| `alpha-vantage` | [官方 MCP](https://mcp.alphavantage.co/) | 取得帳戶設定及 API plan, 核對資料延遲 / quota, secret 不放 URL |
| `jquants-docs` | [官方文件 MCP](https://github.com/J-Quants/j-quants-doc-mcp) | Python 3.10+ / uv 或 pip, pin source, 查 API 文件 |
| `jquants-api` | [官方行情 API](https://www.jpx.co.jp/english/markets/other-data-services/j-quants-api/index.html) | 行情帳戶 / plan / API version, 時間與調整欄位 |
| `twse`, `tpex` | [TWSE](https://openapi.twse.com.tw/) / [TPEx](https://www.tpex.org.tw/openapi/) 官方 API | 選 Swagger dataset, 保存日期, 時區, 幣別, 調整及來源授權 |
| `angular` | [官方 CLI MCP](https://angular.dev/ai/mcp) | 以目標專案版本確認 `mcp` 指令, 使用 project CLI, 不全域升級 |
| `supabase` | [官方 MCP](https://supabase.com/docs/guides/ai-tools/mcp) | 選開發 project, `project_ref` / `read_only=true` 與 tool groups |
| `neon` | [官方 MCP](https://neon.com/blog/give-your-agent-neon-tools) | 選開發 project / branch, `projectId` / `readonly=true` 與 tool categories |
| `ecpay-skill` | [官方 API Skill](https://github.com/ECPay/ecpay-api-skill) | 核對 license / Codex setup, 測試商店, callback 驗簽及 idempotency, 實際付款另依授權 |
| `pubmed` | [NCBI 官方 API](https://www.ncbi.nlm.nih.gov/home/develop/api/) | 文獻 quota, PMID / DOI, 研究品質與適用條件 |
| `cochrane`, `nice` | [Cochrane](https://www.cochranelibrary.com/) / [NICE](https://www.nice.org.uk/guidance) 網站 | 透過 browser / search 查詢研究與臨床指引, 依網站存取權限閱讀原文 |
| `tfda` | [官方仿單網站](https://mcp.fda.gov.tw/) | 核對 permit / 品名與仿單版本, hostname 的 mcp 不是此協定 |

股票預測另需依時間順序回測, 保存 forecast 時點與資料版本, 呈現誤差及區間. 醫療資訊核對研究品質, 指引更新及適用族群, 不由單篇 paper 直接決定結論
