# 自訂 Skills

每個子目錄是一個可獨立安裝的 Skill, `SKILL.md` 定義啟用條件, `agents/openai.yaml` 保存介面資訊, 詳細流程依任務載入 `references/` 或 `scripts/`

保留 focused Skills 的用途、輸入與驗收邊界, Plugin 用於分組交付與選擇性啟用, 不合併成大 Skill. 同一 Skill 避免同時使用獨立與 Plugin 來源, 分組及文件領域的 trigger 範例見 [Plugins](plugins.md#skill-邊界與選擇性啟用)

以此儲存庫為來源, 僅單向同步選定 Skill 到 `$CODEX_HOME/skills/`, 保留 `.system`、第三方 plugin 與其他來源的 Skills. 需要新專案治理時使用 [project starter](../skills/agent-governance/assets/project-starter/README.md), 範本需依實際專案改寫

| 類別 | Skill | 用途 |
|---|---|---|
| Agent 與 context | [Agent Governance](../skills/agent-governance/SKILL.md) | 重整 global, root, nested `AGENTS.md`, tool-specific routing 與 subagent 職責 |
| Agent 與 context | [Task Guide](../skills/task-guide/SKILL.md) | 依實際專案與來源建立功能 / 交易的條件式任務指引, 含跨平台 Markdown 產生器 |
| Agent 與 context | [Task Routing](../skills/task-routing/SKILL.md) | 判斷直接執行, 新 task, fork 與 subagent, 並整理必要交接資訊 |
| Agent 與 context | [Coding Prompt](../skills/coding-prompt/SKILL.md) | 僅在明確要求 prompt 或 handoff 時產生可執行的 coding prompt 與當下 model 建議 |
| Agent 與 context | [Context Brief](../skills/context-brief/SKILL.md) | 將已指定規格, API, schema 或整合文件整理成可重用 implementation contract |
| Agent 與 context | [Jev Evaluation](../skills/jev-evaluation/SKILL.md) | 按需排序候選 context 或進行有限語意分類, 提供 Windows / macOS 共用 MCP 與 CLI |
| 開發工具 | [Development Tool Setup](../skills/development-tool-setup/SKILL.md) | 逐項檢查 Context7, Playwright, RTK 與工作台相依, 以 Python installer 完成已授權的單項安裝及診斷 |
| 開發工具 | [Playwright CLI](../skills/playwright-cli/SKILL.md) | 以具名隔離 session 重現 UI, 核對 snapshot, Console, Requests 與 screenshot |
| 開發工具 | [Packaging Acceptance](../skills/packaging-acceptance/SKILL.md) | 核對來源映射、版本、hash、搬移與退出清理, 依授權選最小或完整驗收 |
| 開發工具 | [Local Activity Query](../skills/local-activity-query/SKILL.md) | 查詢指定 loopback monitor 的期間計數與健康摘要, 保留未知與部分回補狀態 |
| AI 與媒體 | [AI Application Engineering](../skills/ai-application-engineering/SKILL.md) | 實作或診斷 LLM, Agent, Tool Calling, RAG, Embedding 與 model runtime |
| AI 與媒體 | [ComfyUI Workflow](../skills/comfyui-workflow/SKILL.md) | 維護可重現的 Stable Diffusion / ComfyUI graph, model 與硬體設定 |
| AI 與媒體 | [Editorial Illustration](../skills/editorial-illustration/SKILL.md) | 依固定 editorial illustration 視覺方向處理使用者提供的圖片 |
| Frontend 與遊戲 | [Angular Development](../skills/angular-development/SKILL.md) | 依實際 Angular 與 TypeScript runtime 分配 Component, Service, state 與資料轉換責任 |
| Frontend 與遊戲 | [UI UX Design](../skills/ui-ux-design/SKILL.md) | 依實際流程與研究檢查介面, 文案, 原型, responsive 與無障礙, 先驗證小區塊 |
| Frontend 與遊戲 | [Angular Member Order](../skills/angular-member-order/SKILL.md) | 安全整理 Angular Component class member 與可選的 Signal I/O 改寫 |
| Frontend 與遊戲 | [Unity Development](../skills/unity-development/SKILL.md) | 依實際 Unity version, package, serialized asset 與 build target 開發及驗證 |
| Frontend 與遊戲 | [Game Balance Simulation](../skills/game-balance-simulation/SKILL.md) | 共用遊戲規則跑模擬, 比較策略與分布, 重播數值及狀態錯誤 |
| Frontend 與遊戲 | [Vue Development](../skills/vue-development/SKILL.md) | 依實際 Vue, Nuxt 或 Vite stack 開發並保留 component, state, SSR 與 build contracts |
| Frontend 與遊戲 | [React Development](../skills/react-development/SKILL.md) | 依實際 React runtime 處理 component, state, effects, routing 與按需 SSR / hydration |
| 架構與研究 | [System Design Analysis](../skills/system-design-analysis/SKILL.md) | 依需求與來源分析系統邊界, 資料流, 取捨與驗證範圍 |
| 架構與研究 | [Research Learning Synthesis](../skills/research-learning-synthesis/SKILL.md) | 從可追溯來源整理研究, 學習與可採取的結論 |
| 證據與來源 | [Document Source Matching](../skills/document-source-matching/SKILL.md) | 對照來源身分與抽出版, 區分 hash 一致與內容涵蓋 |
| 證據與來源 | [Environment Consistency Check](../skills/environment-consistency-check/SKILL.md) | 比對明確環境範圍, 保留存取失敗與部分掃描狀態 |
| 證據與來源 | [Validation Evidence Review](../skills/validation-evidence-review/SKILL.md) | 檢視驗證證據的來源版本, 結果與未涵蓋範圍 |
| 文件 | [Doc Updater](../skills/doc-updater/SKILL.md) | 實作後依 verified diff 同步必要的 docs, memo, changelog 或 API reference |
| 文件 | [Local Document Processing](../skills/local-document-processing/SKILL.md) | 沿用 versioned document core 擷取文件與預覽安全更新, 核對來源 hash 及寫入範圍 |
| 文件 | [Document Production](../skills/document-production/SKILL.md) | 產生可交付的 PDF, DOCX 或 Markdown 正式文件 |
| 文件 | [Multilingual Proofreading](../skills/multilingual-proofreading/SKILL.md) | 依語言校對台灣繁中, 英文與日文, 保留引用原文與程式碼 |
| 文件 | [README Maintainer](../skills/readme-maintainer/SKILL.md) | 依 repository 證據建立或大幅重整 README |
| 文件 | [License Maintainer](../skills/license-maintainer/SKILL.md) | 依授權與 ownership 證據維護 LICENSE, NOTICE, COPYRIGHT, SPDX 與 README 授權連結 |
| Rules 與 Filter | [Network Filter Rules](../skills/network-filter-rules/SKILL.md) | 維護 AdGuard, uBlock Origin, DNS, hosts 與相似 filter/rewrite rules |


## ChatGPT App 安裝

從 [GitHub Releases](https://github.com/gaze9999/codex-toolkit/releases) 下載 all-skills 組合包並解壓, 若用戶端只接受單一 Skill ZIP, 將要安裝的同名 Skill 目錄另包成 ZIP, 再到 `Plugins → Skills → Create → Upload from your computer` 上傳

單一 Skill 的上傳 ZIP 頂層需保留同名目錄, release 只提供組合包:

```text
skill-name.zip
└── skill-name/
    ├── SKILL.md
    ├── agents/
    │   └── openai.yaml
    └── references/
```

## Desktop / Web

用戶端支援 GitHub repository 安裝時指定:

```text
Repository: gaze9999/codex-toolkit
Skill path: skills/<skill-name>
```

各 Skill 可獨立安裝, 不需要一次載入整個 `skills/` 目錄
