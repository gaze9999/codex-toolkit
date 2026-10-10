# CLI + Skills 與 MCP 的選用

本文件依 2026-10-05 可取得的官方資料, 社群案例與本 repo 既有實作整理. 表中的建議是依工作情境作出的判斷, 使用時仍核對已安裝版本, 目前 client 能力與資料範圍

## 如何決定

Skill 依任務、專案實際技術及選定工具啟用. 平台 / SDK 專用 Skill 只在使用該平台、SDK、工具或明確要求時載入, Agent、React、環境變數、圖表等一般關鍵字不決定 provider、Framework、代管服務或帳戶開通. 選定工具後遵守必要前置流程, 第三方 Plugin 保留原廠來源與更新方式

先沿用目前能完成任務的能力. Coding agent 有 shell, 工作目錄與可讀取的產物時, 可重現的檔案處理, 測試, Git 操作與批次查詢通常適合 CLI + Skills. CLI 提供操作, Skill 保存何時用, 如何驗收與必要的權限邊界

需要 client 原生的工具探索, 型別化參數, 資源讀取或通知, 遠端帳戶連接, 或受限制的 agent 無法使用 shell 時, 再評估既有 MCP / connector. MCP 提供標準化整合與 capability discovery, 實際支援仍由 server 與 client 決定. CLI 也能回傳 JSON, 登入帳戶及保留狀態, 所以這些特性單獨存在時不足以決定採用 MCP. [MCP 官方架構](https://modelcontextprotocol.io/docs/learn/architecture)

兩種介面都符合需求時, 比較相同任務的完成率, 重現步驟, 重試與恢復, 總 input/output 用量, 花費時間及維護成本. 一次只改一個變因, 保留相同 model, 工作台, 頁面, 資料與驗收條件. 權限, 外傳邊界與核准的寫入範圍依實際工具處理位置核對, 不因改用 CLI 或 MCP 而放寬

## 共用流程的判斷

| 流程 | CLI + Skills 適用情境 | MCP / connector 適用情境 | 本 setup 的接法 |
| --- | --- | --- | --- |
| Browser UI 重現與驗收 | 已知 local/dev 流程, snapshot → 操作 → Console / Requests / screenshot, 與既有測試共同使用 | client 原生 browser tools 與頻繁頁面探索更符合使用方式, shell 不可用, 或所選 server 有 CLI 缺少的能力 | [Playwright CLI Skill](../../skills/playwright-cli/SKILL.md), CLI installer 已存在, 官方 MCP 可另外選用 |
| Library / API 文件 | 以公開技術問題按次查 library ID 與 docs, CLI 可讀 JSON | 已有可用且認證完成的 hosted MCP / plugin, client 直接探索及呼叫工具 | Context7 官方支援兩種模式, 沿用已可用入口, 不重複註冊 |
| Git 狀態, diff 與文字搜尋 | `git`, `rg`, 指定 repo 的工作區與遠端差異 | 多 client 需要同一個受限唯讀介面, 或沒有 shell | 保留原生 CLI, 搜尋不足才查支援目標語言的 symbol / references |
| GitHub PR / CI | `gh` 可讀 PR diff, JSON 欄位與失敗 log, 批次查詢與腳本可重現 | client 已有 OAuth connector, 需要官方 toolsets / read-only 模式, 或 CLI 權限不可用 | 優先既有 `gh` 或官方 GitHub MCP / connector, 不自製重複的 PR server |
| 大量 Test / Build 輸出 | RTK 明確 CLI prefix 或 `pipe`, 保存原始 log 與原命令 exit code | agent 需要結構化呼叫既有文字 / 核准 log 的受限 adapter | RTK CLI 與本 setup adapter 共用同一 binary, 預設不用 hooks |
| 文件轉 Markdown / OCR | 已安裝文件核心的 CLI 做單次 / 批次擷取, 明確來源與輸出位置 | 多 client 反覆查文件與章節, 需要 server 的 root / hash 檢查 | 沿用 python-tools 與 Local Documents 共用核心, 不重做轉換引擎 |
| 抽出版定位, Markdown 檢查與安全更新 | 明確路徑 / hash, batch check, diff / preview / 限定更新範圍 | 有效的 structured tools 能減少反覆解析, 且維持同一權限與 hash 前置條件 | [Local Documents](../usage/local-documents.md), [來源比對](../../skills/local-document-processing/references/source-matching.md) |
| Skills / 環境差異 | repo audit, 版本與 hash 比對, 同步依另外授權的預覽與備份流程處理 | 跨 client 反覆盤點, Workspace Inspection 提供已設定 roots 的受限唯讀查詢 | [唯讀環境比對](../../skills/validation-evidence-review/references/environment-comparison.md), 未設定 roots 的 MCP 保留 pending 狀態 |
| 驗證證據彙整 | 讀既有 JSON / log, 核對 commit / baseline 與未涵蓋項目 | 多 client 反覆查同一份 evidence index | [Validation Evidence Review](../../skills/validation-evidence-review/SKILL.md), 不因查紀錄而重跑測試 |
| 效能與即時資料 | 既有測試或量測入口, 比較同一 fixture 的 CPU 時間、耗時、I/O 與更新結果 | 需要現有瀏覽器 / profiler 的 trace、程序歸屬或受限結構化指標 | [效能與串流參考](../../skills/test-strategy/references/performance-and-streams.md), 程式 I/O 與實體磁碟證據分別核對 |
| 中英日校對 | 本機 textlint / CSpell 與專案詞表, 檔案批次檢查 | 已有 textlint typed lint / fix 工具, client 不具 shell 或需要回傳修正版內容 | [校對 Skill](../../skills/multilingual-proofreading/SKILL.md), CLI fix 寫檔與 MCP 回傳內容分別核對 |
| 本機圖表與產物 | Mermaid CLI 或既有繪圖工具產生可攜檔案 | 需要所選服務的 hosted 編輯, 帳戶或互動能力 | 先確認格式 / browser 相依與外傳範圍, 不因 catalog 有 hosted MCP 就上傳資料 |
| Jev 有限排序 / 分類與監看資料 | 已安裝核心的 CLI, 明確輸入 / rubric 或 HTTP / JSON 唯讀查詢 | 多 client 共用已認證工具或受限資料源, 需要 typed tool discovery | 共用核心與既有服務, 排程及長期監看由 monitor / scheduler 負責, MCP 本身不提供排程 |

文件, 抽出版, 環境與證據列的判斷來自本 repo 現有 adapter / Skill 與共用核心分工. 單次原生操作成本低時直接用 CLI, 實際有重複的結構化存取需求再沿用 MCP, 不為每個 shell 命令加 server

## 官方資料與社群討論如何影響判斷

| 來源 | 可核對的內容 | 採用方式 |
| --- | --- | --- |
| [Microsoft Playwright CLI](https://github.com/microsoft/playwright-cli) 與 [Playwright MCP](https://github.com/microsoft/playwright-mcp) | 官方建議 coding agent 可先採 CLI + Skills, MCP 可用於持續探索與豐富 introspection. CLI 具名 session 也保留 cookies / storage | bounded UI flow 優先 CLI, 依 client / server 的真實能力決定是否需要 MCP, 不把 session persistence 視為 MCP 專屬 |
| [Context7 CLI](https://github.com/upstash/context7/blob/master/packages/cli/README.md) | `ctx7 library`, `ctx7 docs` 與 JSON, CLI + Skills / MCP setup, 各模式的登入及部署限制 | 文件查詢兩種入口皆可, 沿用已能完成任務的入口. `setup` 會寫設定與安裝 Skill, 查文件不需要順便執行 setup |
| [GitHub CLI PR](https://cli.github.com/manual/gh_pr_view), [CI log](https://cli.github.com/manual/gh_run_view) 與 [官方 MCP](https://github.com/github/github-mcp-server) | CLI JSON / logs 與 MCP toolsets / read-only 設定 | CLI 能完成的 PR / CI 查詢先沿用, 原生 client 整合有具體效益時選官方 MCP |
| [RTK](https://github.com/rtk-ai/rtk) | 輸出過濾與估算壓縮率, 官方亦區分輸出減少與整體帳單減少 | 保存原始錯誤與 exit code, 不將輸出壓縮率直接換算為任務省費比例 |
| [MarkItDown](https://github.com/microsoft/markitdown), [textlint](https://github.com/textlint/textlint), [CSpell](https://github.com/streetsidesoftware/cspell) 與 [Mermaid CLI](https://github.com/mermaid-js/mermaid-cli) | 已有本機 CLI 與檔案產物的工具 | 先核對既有核心及所需格式 / 規則, 不為 CLI 已覆蓋的單次工作安裝另一套引擎 |
| [社群討論: Playwright CLI / MCP 比較](https://www.reddit.com/r/Playwright/comments/1vx2wew/playwright_mcp_vs_playwright_cli_the_comparison/) | 討論 running test / mocks 的接續, session 提早關閉, 以及總 input/output 成本未必隨單次 input 降低 | 作為需要驗證的情境, 依已安裝版本 help 與實測確認 attachment / test lifecycle, 不直接採用留言中的旗標或成本比例 |
| [Windows session 案例 #364](https://github.com/microsoft/playwright-cli/issues/364), [版本啟動案例 #42402](https://github.com/microsoft/playwright/issues/42402) 與 [Skill 旗標案例 #243](https://github.com/microsoft/playwright-cli/issues/243) | session、runtime / startup 與旗標行為依工具版本確認 | Windows 安裝後必須實測跨次 open / snapshot / 操作 / close, 以目前版本 help 與實際操作結果為準 |

官方資料用來確認功能與支援範圍, 社群資料用來找重現條件與失敗案例. 兩者共同支援選用判斷, 效率結論仍需本機相同任務的量測

## 可重現的本機操作

安裝與更新仍走 [development-tool-setup](../../skills/development-tool-setup/SKILL.md) 的單項 preview / apply. 套件版本與相依以 [requirements](../../mcp/tools/development-tools.requirements.json) 為準. 操作已安裝工具時不自動執行全套 setup, OAuth, hooks 或其他工具安裝

在指定 repository 執行 Git / GitHub 的唯讀查詢:

```text
git status --short --branch
git diff --stat
gh pr view <number> --json number,title,state,baseRefName,headRefName
gh pr diff <number>
gh run view <run-id> --log-failed
```

PR / CI 查詢先核對 repository, host 與帳戶. 查詢不授權建立留言, merge 或發佈. 文件, hash, JSON 與本機詞表檢查沿用相符核心及範圍, 檢查 command help 與寫入行為後再操作

本 repo 的 [Playwright CLI 操作參考](../../skills/playwright-cli/references/commands.md) 保留具名 session, snapshot ref, Requests 與限定清理. Repo `skills/` 是可版控來源, 本機 Skill 是單向鏡像, 同步後的 client discovery 依實際載入結果確認
