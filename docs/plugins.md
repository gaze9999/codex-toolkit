# Plugins

Plugin 使用一份 canonical Skills 來源與明確的資源映射. `plugins/catalog.json` 是本儲存庫的來源清單, 每個 `plugins/ID/plugin.json` 是可攜 manifest, 實際自含套件由 Release 流程產生. 格式依 [OpenAI Plugin 封裝說明](https://developers.openai.com/plugins/build/plugins)

| 批次 | ID | 內容 | 來源狀態 |
|---|---|---|---|
| 0 | `packaging-acceptance` | 封裝、來源、搬移與程序生命週期驗收 Skill | 已定義 |
| 1A | `jev-evaluation` | 既有 Jev Skill、CLI、MCP 原始碼與操作流程 | 已定義 |
| 1B | `documents-specifications` | Context Brief、來源比對、文件更新與安全擷取流程 | 已定義 |
| 1B | `environment-evidence` | 環境比對、證據檢視與有效性判斷 | 已定義 |
| 1C | `frontend-engineering` | Angular、React、Vue、UI UX、Playwright Skills | 已定義 |
| 2 | `agent-workflow` | Governance、Coding Prompt、Task Routing、Task Guide 與需求 / 決策關係 | 已定義 |
| 2 | `multilingual-proofreading` | 繁中、英文、日文 Skill、詞庫與規格文案保護規則 | 已定義 |
| 3 | `local-activity` | 明確期間的唯讀活動摘要 helper | 已定義 |
| 4 | `project-documentation` | README 與授權文件維護, 保留各自的 focused Skill | 已定義 |
| 3 | `workbench-ui` | 共用 UI 串接 Skill | 待公開散布授權, 不加入發布包 |

來源已定義不代表已發布、安裝、啟用或目前 client 已載入. 預設套件只提供 Skills 與資源, `runtime_profiles` 列出既有 setup 的選用入口, 不會自動註冊 MCP 或另外複製 document / workspace core. Jev 呼叫需要原有帳戶設定, 文件與證據使用已安裝的 versioned core, Serena、DevTools 按任務需要選用

## Skill 邊界與選擇性啟用

保留 focused Skills, trigger、輸入或驗收不同時維持獨立流程, 優先修正重疊的 description 與排除條件. Skill 名稱與 description 用於選擇, 選中才讀取 `SKILL.md`, 深入資源依任務載入. 參考 [Skill 設計](https://developers.openai.com/plugins/build/skills) 與 [Codex Skill 載入](https://learn.chatgpt.com/docs/build-skills)

Plugin 管理交付、版本與選擇性啟用. 分組依共同工作流程、相依與更新需求, 不只依資料夾名稱. `project-documentation` 包含互相轉介的 README 與 License Skills, README 維護不授權選擇或變更授權條款. 同一 Skill 在同一環境選用獨立安裝或 Plugin 來源, 避免重複啟用. 參考 [Plugin 架構](https://developers.openai.com/plugins/concepts/plugins)

Canonical 來源保留在 `skills/`, Plugin 產物依 catalog 生成, 保存來源 revision、檔案清單與 SHA-256, 不手改生成副本. Python 用於重複且確定的檔案、metadata、引用與 manifest 檢查, 不以字詞相似度取代語意 routing, 也不因檔案多就新增 preprocessing

打包本身不證明 context、token 或 subscription 額度下降. 使用相同任務與驗收比較成功率、首次通過率、時間、可取得的 usage、人工修正與 regression, 取不到的額度標示 unknown, 不把 token 降幅當成額度降幅

文件領域可用以下需求核對 trigger, 再檢查對應輸出與授權邊界. 來源與結構檢查分開記錄, 實際模型觸發、操作品質與額度效益需另有執行證據

| 需求 | 主要 Skill | 邊界 |
|---|---|---|
| 擷取指定 PDF / Office 原文或表格 | `local-document-processing` | 不推導新規格或自動重抽可用來源 |
| 找原始檔對應的既有 Markdown, 核對 hash | `document-source-matching` | 唯讀, 不重新轉換或改寫 |
| 依確認的欄位規格建立實作用 Context Brief | `context-brief` | 保存規格與來源, 不當進度交接 |
| 依已完成 diff 更新指定 API 文件 | `doc-updater` | 已有目標與明確更新 / 同步授權, 不大幅重整 README |
| 重整 README 的安裝與使用說明 | `readme-maintainer` | 依實作證據, 不自選授權條款 |
| 核對 NOTICE 或修正 README 授權連結 | `license-maintainer` | 不推定 ownership 或改變授權 |
| 交付可下載的正式 PDF / DOCX 報告 | `document-production` | 實際產檔, 不以聊天草稿交付 |
| 只說明程式碼, 未要求文件 | 依實際技術工作選擇 | 不自動新增文件或啟用整組 Skills |

## 行為驗收案例

修改前後用相同需求與來源核對以下情境, 依任務另加必要案例. 這是驗收設計, 實際執行才記結果, 人工語意複核, 結構檢查與模型行為比較分開記錄, 不以文件變短推論成功率、token 或額度效益

保留 doc-updater 現有篇幅與分層, 不設定字數目標. history / ID 與 Notion 操作細節的搬移先列候選, 有實際誤判、漏讀或重複載入證據時再比較, 授權與規格判定規則仍留在入口

比較時固定 model、reasoning、工具與權限、起始文件及變更證據, 記錄基準與候選來源的 revision 或 hash, 每次從獨立的相同起始副本執行, 一次只改一個變因. Notion 邊界案例先使用本機模擬回應與呼叫紀錄, 真實帳戶驗證另依當次授權處理

| 情境 | 預期行為與驗收界線 |
|---|---|
| 明確要求更新或以其他說法要求對齊既有文件, 已有證據與目標 | 選用 doc-updater, 只修改有證據關聯的內容, 兩種說法都能完成相同目標 |
| 要更新文件, 缺 implementation evidence 或明確目標 | 只補必要資訊, 不捏造變更或任意選文件 |
| 本機文件含 Notion 連結、page ID、snapshot 或 sync_mode, 本次未要求 Notion | 完成已授權本機更新, Notion 探索、讀取、比較、驗證與寫入呼叫皆為零, 不回報遠端狀態 |
| 先前同步已暫停, 本次只要求更新本機文件 | 不因既有配對或歷史同步紀錄恢復 Notion 操作, 保留本機 metadata, 不推定遠端狀態或更新同步時間 |
| 本次明確要求同步指定本機與 Notion 目標 | 只處理指定目標, 寫入前核對現況, 保留獨立變更, 寫入後讀回, 不擴大探索其他頁面 |
| 程式行為與規格衝突 | 保留規格判定權, 指出衝突及影響, 只更新獨立且已授權的實作 / 狀態內容 |
| 讀取後、寫入前另有修改加入目標文件 | 重新核對版本, 保留新增的無關內容, 有衝突時停止受影響範圍的寫入, 不以舊快照覆寫 |
| 只有 diff, 沒有執行 / 部署證據 | 記來源變更, 不宣稱測試、API、持久化或部署成功 |
| Plugin 候選盤點 | 說現況、比較與依據, 必要時建議優先序, 不強選單一方案或把定義當安裝 |
| 已有未提交的 Skill 簡化候選 | 說現有改動、有效決定與待驗收, 不只回本次未改檔 |
| 前端實作只有部分檢查通過 | 分實作與驗收完成, 分測試、資料組合與批次, 判定未跑項目是否為必要驗收, 比較結論須有基準 |

先確認觸發、授權、規格判定、並行修改保護與回報正確性. 候選若漏掉核心規則或造成驗收退步, 停止採用並保留基準, 通過後才比較時間、額外讀取、重試與可取得的 usage. 比較結果記錄實際輸出、檔案差異、工具呼叫與未涵蓋範圍, 未執行的案例保留待驗收

## 預覽與最小檢查

```text
launch-cli.cmd plugins --list
launch-cli.cmd plugins jev-evaluation
python -B mcp/scripts/prepare_plugin_release.py --check
```

Windows 也可用 `launch-cli.ps1`, macOS 用 `sh launch-cli.sh`. CLI 同時呈現來源定義與本機已設定 Plugin, 選定項目可檢查來源檔案、版本與 hash. 已直接安裝同名 Skills 時會提示重複來源, Plugin 的實際載入狀態須由 Codex 用戶端確認

`--check` 只在記憶體內檢查 manifest、Skill owner、選用 runtime 名稱、資源、hash 與 Markdown 內部引用, 不建立套件目錄或壓縮檔. 明確選取待授權項目會拒絕發布

## Release 與安裝來源

`.github/workflows/plugin-release.yml` 對發布的 Release 在 Linux、Windows 與 macOS 檢查來源, 由 Linux 為 catalog 中可封裝項目產生 Plugin ZIP、組合 Marketplace ZIP 與各自 SHA-256 檔. 手動 workflow 只檢查指定 revision, 不發布

封裝來源必須是乾淨、已提交的版本. 每個套件內的 `source-manifest.json` 保留版本、commit、來源映射與逐檔 SHA-256, 組合包另包含 `.agents/plugins/marketplace.json` 與 `plugin-release-manifest.json`. 上傳前逐一讀回壓縮檔, 核對完整檔案集合、內容與 checksum

```text
codex-toolkit-plugins.zip
├── .agents/plugins/marketplace.json
├── plugin-release-manifest.json
└── plugins/codex-ID/
    ├── plugin.json
    ├── source-manifest.json
    ├── skills/
    └── resources/  (有資源的項目)
```

從本儲存庫的 GitHub Release 下載已發布的組合包, 核對 checksum 後解壓. 使用當前 Codex 支援的 Marketplace / Plugins 入口加入解壓根目錄, 選取並啟用指定項目. 不直接把來源清單當成 Marketplace, 也不把 `plugins/ID` 的 manifest 目錄當成已包含 Skills 的套件

安裝驗收依序核對來源、設定註冊、啟用、重開 client 後的載入及離線 helper, 移除後再確認 Plugin 已消失且獨立 Skills / MCP runtime 保留. Jev 離線檢查不呼叫付費 API, 真實評估另列帳戶授權與呼叫結果. 發布、安裝、移除與跨平台搬移各記錄對應證據, 不以來源檢查替代

## 活動與 Workbench UI 邊界

活動 helper 只讀取明確指定、已在執行的 HTTP loopback monitor, 支援 `1h`、`24h`、`7d`、`all`, 不啟動監測、不修改設定, 不輸出對話內容、標題、完整錯誤、檔案路徑或帳戶總量. 未知值保留 null, 回應大小與連線時間有上限

Workbench UI Plugin 的共用串接流程仍待公開散布授權, 保留來源定義, 不加入發布包. 讀取 private 儲存庫的權限不代表公開散布授權

## 已安裝 Plugin 的本機同步

已註冊的自有 Plugin 可使用共用 CLI 入口, 預設只預覽來源差異, 不新增安裝

```text
launch-cli.cmd plugins --sync-installed
launch-cli.cmd plugins --sync-installed --plugin agent-workflow
launch-cli.cmd plugins --sync-installed --plugin agent-workflow --apply
```

macOS/Linux 使用 `sh launch-cli.sh` 的相同參數, setup wheel 含此入口時使用 `codex-setup`, 既有舊版先用更新後的來源 CLI. `--plugin` 可重複選定已註冊項目, 省略時選目前已註冊的自有範圍, `--yes` 僅用於已授權的 `--apply`

預覽以 JSON 列出來源版本、變更檔、保留項目及原生重新安裝範圍. 原生 CLI 替換同名 Marketplace 需移除再加入, 因此重新安裝涵蓋目前所有註冊項目, 未選項目沿用舊快照內容. 套用先核對來源及目標有無新修改, 保存新快照與設定備份, 透過原生 Codex 命令註冊及安裝, 再核對完整項目、啟用狀態與快取內容. 失敗時以原生命令復原舊來源並核對, 不整檔覆寫設定或直接改快取

此入口適用既有本機 `codex-toolkit` Marketplace 且項目為標準啟用設定. 停用或自訂設定、Git Marketplace、初次安裝與帳戶串接保留原生介面, 不猜測設定遷移方式. 其他設定如在交易期間另有變動, 回報實際差異核對狀態

快照標記 `working-tree`, 保存來源 HEAD 與逐檔 hash, 不代表 commit 或 Release. 正式發布仍遵循乾淨已提交來源的門檻. 新來源、快取核對、client 重新載入與模型行為分開回報, 舊來源及備份保留供復原

既有可用 Plugin 優先從支援的入口引用及重用. 相同 Skill 維持單一啟用 owner, 不因同步多裝直接副本. 需要獨立散布或格式不支援外部引用時, 才由 canonical payload 產生可獨立使用的版本鏡像, 記錄來源、hash 與授權, 不依賴會變動的 client 快取絕對路徑
