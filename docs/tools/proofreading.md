# 中英日文字校對

文字校對依語言分開設定, 繁中使用台灣詞表, 中文並列可保留頓號 `、`, 其他標點採半形. 英文檢查拼字與專案術語, 日文保留 `、。` 與原有文體, 混合語言先按內容分段選用規則

| 選項 | 接法 | 用途 |
| --- | --- | --- |
| `textlint` | [textlint 官方 MCP](https://textlint.org/docs/mcp/) 15.8.0, [prh](https://github.com/textlint-rule/textlint-rule-prh) 6.1.0, Node 20.18+ | 台灣用語詞表與繁中半形標點, 本機處理 |
| `textlint-ja` | 同一官方引擎, 獨立 [日文規則集](https://github.com/textlint-ja/textlint-rule-preset-ja-technical-writing) 12.0.2 | 助詞, 文體與日文技術寫作, 保留日文標點 |
| `cspell` | [CSpell CLI](https://cspell.org/docs/how-it-works) 10.3.6, Node 22.18+ | 英文拼字與產品詞表, 本機處理 |
| `languagetool` | [LanguageTool](https://dev.languagetool.org/http-server), 另選本機 Java 服務或核准的雲端服務 | 需要時補英文文法檢查, 語言支援不代表完整繁中或日文拼字檢查 |

Windows 使用 `launch-cli.cmd mcp`, macOS / Linux 使用 `sh launch-cli.sh mcp`, 在文字校對類別選擇一項, 每次只安裝該項及相依, 也可由既有 development-tool installer 指定同名選項

設定集中於 [tools/proofreading](../../mcp/tools/proofreading), 安裝後複製到所選 npm prefix 的 `proofreading/zh-tw`, `proofreading/ja` 或 `proofreading/en`, 各 profile 獨立保存, 既有專案規則仍可沿用, 本機自行修改的設定不會被 installer 靜默覆寫

繁中詞表涵蓋軟體, 硬碟, 滑鼠, 記憶體, 資料夾與資料庫等用語, 標點規則保留中文並列的頓號及檔名, 版本與小數的句點, 分號只提示依語意修改, 不自動猜測分句, 日文段落不套繁中規則

textlint 先用 lint 工具檢查完整規則, 再用 fix 工具取得可自動修正的內容, 不直接覆寫原檔, 文體等無法自動修正的問題仍需依 lint 結果處理, 修正後再跑 lint 確認. 引用原文, 專有名詞與程式碼保留其來源形式, blockquote 與 code 的檢查範圍依各規則設定, inline 引用或混合語言的修正仍需逐項確認. [官方 fix 行為](https://textlint.org/docs/mcp/), [prh 規則](https://github.com/textlint-rule/textlint-rule-prh)

已有 textlint CLI 時, bounded 檔案 / batch check 可沿用相同規則, 先查 `textlint --help` 與專案設定, `--fix` 可能直接寫檔. 本 setup 的既有 MCP lint / fix 工具適合 client 需要 typed result 或回傳修正內容的情境, 不因 CLI 與 MCP 都可用而重複執行整套檢查. 詳細選用條件見 [CLI / MCP 指引](selection.md)

接法使用官方 textlint MCP, setup 的啟動層依官方 output schema 整理 fix 回傳內容, 保留官方工具與修正結果, 不修改安裝的上游套件

英文可使用安裝後 `proofreading/en/cspell.json` 或專案既有詞表, LanguageTool 須確認文字處理位置與選定服務條件, 官方列中文與日文沒有拼字檢查. [語言支援](https://help.languagetool.org/hc/en-us/articles/39254526141463-What-languages-does-LanguageTool-support)

[Multilingual Proofreading Skill](../../skills/multilingual-proofreading/SKILL.md) 負責依語言選能力, 逐項判斷規則結果, 再做語意與事實複核, 不固定每個專案都使用同一工具

## 文件交付前的校對

製作或改寫文件時, 交付前須使用可用的 textlint 或同等語言 / 用詞檢查工具, 再人工複核語意. 繁中採台灣用語, 包含 README, 技術文件, 摘要, task guide 與 PDF / DOCX 的自撰文字來源. 檢查新增或改寫的內容, 保留既有文件中的原始引用, 程式碼, 欄位名稱與正式文件名稱

工具未安裝, 不支援目標語言或執行失敗時, 提醒使用者實際缺項與尚未完成的自動檢查, 仍完成可行的人工校對. 敏感內容可略過工具檢查, 不傳送至外部服務或寫入 lint 暫存檔, 以人工複核台灣用詞並說明已略過的範圍

## 規格與介面文案保護

規格書或已確認介面定義的標題, 欄位名稱, 按鈕, 狀態及提示文字須保留原文, 包含 HTML element 的文字與標點. 只有明確的文案修改要求才可更動, textlint 的用詞或標點提示須先核對來源與授權, 不直接套用到固定文案

繁中設定加入 [protected-copy.cjs](../../mcp/tools/proofreading/zh-tw/protected-copy.cjs) filter, 保留 Markdown 中 HTML element 的內容, 包含行內 span 及巢狀標籤. 未閉合標籤保護到文件結尾, 須先人工確認結構, 周邊自撰說明仍接受詞表與標點檢查. [textlint 官方 filter API](https://textlint.org/docs/filter-rule/)

已知的純文字規格文案可在專案設定中以 filter 的 `texts` 陣列列出完整文字, 保護原字串及含該文案的文字節點, 避免含前後文的規則跨入文案範圍. 同節點的自撰說明需拆分檢查, 不改寫共用 setup 的預設設定. 以下是設定片段, 沿用其他既有 rules, 並依實際安裝位置解析 filter 路徑:

```javascript
filters: {
  [path.join(profileDirectory, 'protected-copy.cjs')]: {
    texts: ['規格定義的完整標題'],
  },
},
```

未建立保護清單的規格文案, 在校對輸入中保留為 inline code 或 blockquote, 或只檢查周邊自撰說明. 不改寫權威來源來配合詞庫, fix 結果套用前逐項核對固定文案, 欄位名稱及原始引用. 檢查 Markdown / 純文字不會自動辨識文案的規格來源, HTML / Angular 原始檔的 parser 與修改範圍另行核對

## 一般回覆與 agent 指引

[Global 指示來源](../../agents/AGENTS.md) 的 "語言與回覆" 明確要求一般回覆, 進度更新, 文件及 Main / subagent 的使用者可見交付採台灣用詞, 軟體整合使用串接, 送出前依上下文複核. 各角色沿用適用指示, 詳細轉換規則集中於共用詞表

例如描述軟體工具整合時寫 "完成工具之間的串接", 描述設定時寫 "MCP 設定". 實體線路的接線, 數學上的接線, 記憶體配置, 原始引用, 正式名稱與程式碼依原意保留. 詞庫的 pattern 只提示明確語境, 未命中的用詞仍需人工判斷

一般回覆、進度與 handoff 由 agent 複核繁體字、語意與台灣用詞, 窄詞表補上關卡、來源、沒有與歷史等已觀察混用, 保留引用、Symbol 及規格文案, 詞表不是完整簡繁轉換器. textlint 詞庫在執行校對時載入, 安裝詞庫不會自動檢查每則聊天訊息. 文件製作與改寫仍須執行前述交付前校對, 敏感內容依該節的例外處理

Global 與 Skill 的來源及本機鏡像依 [Agent 同步說明](../agents.md) 管理. 檔案同步後須讓使用端重新載入指示, 已開啟對話的載入狀態另行核對, [OpenAI 指示載入文件](https://learn.chatgpt.com/docs/agent-configuration/agents-md) 說明 Codex 啟動時建立指示鏈的行為

## 共用台灣用詞

共用詞表位於 [terms.yml](../../mcp/tools/proofreading/zh-tw/terms.yml), CLI 與 MCP 載入同一份 prh 規則. 詞表以台灣開發文件與辭典釋義確認語境, 涵蓋文件製作, 程式開發, 套件管理, CLI 操作與網路診斷. 每筆規則保留轉換範例, 多義詞另列應保留的反例

| 語境 | 提示用法 | 建議用法 |
| --- | --- | --- |
| 軟體整合與設定 | `MCP 接線`, `MCP 配置`, `默認值`, `配置文件` | `MCP 串接`, `MCP 設定`, `預設值`, `設定檔` |
| 資訊與訊息 | `版本信息`, `錯誤信息`, `用戶權限` | `版本資訊`, `錯誤訊息`, `使用者權限` |
| 資料結構與快取 | `緩存`, `哈希`, `字符串`, `數組`, `事件隊列`, `堆棧` | `快取`, `雜湊`, `字串`, `陣列`, `事件佇列`, `堆疊` |
| 編碼與型別 | `字節`, `布爾值`, `字符編碼`, `正則表達式`, `資料類型` | `位元組`, `布林值`, `字元編碼`, `正規表示式`, `資料型別` |
| 程式操作 | `回調函數`, `調用 API`, `JSON 對象`, `for 循環`, `代碼審查` | `回呼函式`, `呼叫 API`, `JSON 物件`, `for 迴圈`, `程式碼審查` |
| 套件與建置 | `軟體包`, `插件`, `套件依賴關係`, `構建產物` | `套件`, `外掛`, `套件相依關係`, `建置產物` |
| 程式診斷 | `子進程`, `後台進程`, `系統日誌`, `日誌文件` | `子處理程序`, `背景處理程序`, `系統記錄`, `記錄檔` |
| 本機與 CLI | `本地環境`, `命令行工具`, `開啟終端`, `只讀模式` | `本機環境`, `命令列工具`, `開啟終端機`, `唯讀模式` |
| 檔案與資料操作 | `文件路徑`, `CSV 導入`, `導出 JSON`, `字段`, `單元格` | `檔案路徑`, `CSV 匯入`, `匯出 JSON`, `欄位`, `儲存格` |
| 網路操作 | `HTTP 協議`, `TCP 端口`, `IP 地址`, `API 訪問`, `連線超時` | `HTTP 通訊協定`, `TCP 通訊埠`, `IP 位址`, `API 存取`, `連線逾時` |
| 媒體與介面 | `視頻檔案`, `視頻通話`, `使用者界面`, `UI 組件`, `頁面刷新` | `影片檔案`, `視訊通話`, `使用者介面`, `UI 元件`, `頁面重新整理` |
| repository 與 API | `Git 倉庫`, `API 契約` | `Git 儲存庫`, `API 規格`, 依既有技術寫作偏好選用 |

詞義不同時保留原意. `默認這項決定` 表示默許, `同學的信息` 表示音訊, `用戶端` 指 client, `電信用戶` 指訂戶, `導出公式` 是推導, `數學函數` 是數學名詞. `硬體元件接線`, `控制系統接線`, `程式配置記憶體`, `物體質量`, `地層界面`, `服務對象`, `交易代碼`, `案件類型`, `血液循環`, `旅行日誌`, `本地居民`, `本地化`, `刷新紀錄` 與法律契約均依語境保留

快取與緩衝區分別依 cache 與 buffer 選用, 影片檔案與視訊通話分開處理, 字串與字元也保留不同意義. 程式中的 user 採使用者, client 保留用戶端, 產品既有的客戶端用法可保留. plugin 採外掛, extension 與 add-in 保留產品的擴充套件, 延伸模組或增益集名稱. `函數`, `程序`, `行程`, `本地` 與 `日誌` 等詞須先確認用途再轉換

來源文件, 正式文件名稱, 導入新工具與實體倉庫依原意保留. 單獨的配置, 對象, 文件, 代碼, 信息, 用戶與 contract 需依上下文判斷. 技術寫作中的契約依 API 規格, 介面規格, 欄位規格, 資料格式或相容性要求選用, 正式名稱另行複核. 轉手, 鋪平等抽象說法則人工改寫為呼叫端, 使用端, 修改範圍, 只多包一層或直接展開至呼叫端等具體描述

日文採日文標點與文體, 英文採英文慣例, 混合語言依段落選擇設定. 原始引用, 程式碼, URL, Symbol 與正式名稱保留來源形式. Markdown blockquote, inline code 與 code block 依目前設定保留, inline 引用仍逐項複核

## 用詞來源與判斷方式

2026-10-05 查閱下列來源. 辭典用於判斷一般詞義, 開發文件用於核對軟體語境, 產品介面與既有專案用語依其適用範圍採用. 官方繁中頁面的譯詞也可能混用, 收錄時逐詞比對語意與實際用法

| 詞庫來源 ID | 查閱來源 | 採用依據 |
| --- | --- | --- |
| `moe-default` | [教育部國語辭典簡編本: 默認](https://dict.concised.moe.edu.tw/dictView.jsp?ID=3778&la=0&powerMode=0) | 保留默許或認可的詞義, default 的軟體語境採預設 |
| `moe-information` | [教育部國語辭典簡編本: 信息](https://dict.concised.moe.edu.tw/dictView.jsp?ID=27821&la=0&powerMode=0), [重編國語辭典修訂本: 資訊](https://dict.revised.moe.edu.tw/dictView.jsp?ID=137246&q=1&word=%E8%A8%8A) | 一般音訊保留, 軟體 information 採資訊 |
| `naer-message` | [教育百科: 訊息, 國家教育研究院資訊與通信術語辭典](https://pedia.cloud.edu.tw/Entry/Detail/?search=%E8%A8%8A&title=%E8%A8%8A%E6%81%AF%EF%BC%9B%E4%BF%A1%E6%81%AF) | message 採訊息, 與資訊區分 |
| `naer-queue` | [教育百科: 佇列, 國家教育研究院圖書館學與資訊科學大辭典](https://pedia.cloud.edu.tw/Entry/Detail/?search=%E5%88%97&title=%E4%BD%87%E5%88%97) | 資料結構的佇列與堆疊 |
| `moztw` | [Mozilla 台灣社群詞彙表](https://moztw.org/docs/glossaries/) | 依台灣用法與表意選詞, 個別產品名稱依其介面確認 |
| `mdn`, `mdn-array` | [MDN 繁中術語表](https://developer.mozilla.org/zh-TW/docs/Glossary), [JavaScript Array](https://developer.mozilla.org/zh-TW/docs/Web/JavaScript/Reference/Global_Objects/Array) | 陣列, 字串, 正規表示式, 元素, 物件與字元 |
| `mdn-cache` | [MDN: Cache 快取](https://developer.mozilla.org/zh-TW/docs/Glossary/Cache) | cache 採快取, 與緩衝區區分 |
| `mdn-callback`, `mdn-async` | [MDN: 回呼函式](https://developer.mozilla.org/zh-TW/docs/Glossary/Callback_function), [非同步 JavaScript](https://developer.mozilla.org/zh-TW/docs/Learn_web_development/Extensions/Async_JS/Introducing) | 函式, 回呼, 非同步, 事件佇列與呼叫 |
| `android-security` | [Android Developers 安全性指南](https://developer.android.com/privacy-and-security/security-tips?hl=zh-tw) | 使用者, 用戶端, 雜湊, 緩衝區, 存取與資料格式 |
| `bitarray` | [Microsoft Learn: BitArray](https://learn.microsoft.com/zh-tw/dotnet/api/system.collections.bitarray?view=net-10.0) | 布林, 位元, 堆疊與堆積 |
| `dotnet`, `command-line` | [C# 一般結構](https://learn.microsoft.com/zh-tw/dotnet/csharp/fundamentals/program-structure/), [命令列安裝參數](https://learn.microsoft.com/zh-tw/ssms/install/command-line-parameters), [async](https://learn.microsoft.com/zh-tw/dotnet/csharp/language-reference/keywords/async) | 型別, 建置, 命令列, 執行與呼叫端 |
| `dependencies`, `gateway-plugin` | [相依性與連結庫](https://learn.microsoft.com/zh-tw/dotnet/standard/library-guidance/dependencies), [閘道外掛程式](https://learn.microsoft.com/zh-tw/windows-server/manage/windows-admin-center/extend/develop-gateway-plugin) | 相依關係, 相依套件, 外掛, 自訂與設定檔 |
| `boot-events` | [Microsoft Learn: 安裝與開機事件集合](https://learn.microsoft.com/zh-tw/windows-server/administration/get-started-with-setup-and-boot-event-collection) | 記錄, 記錄檔, 設定檔與命令列 |
| `excel-data` | [Microsoft Support: 資料如何透過 Excel 傳輸](https://support.microsoft.com/zh-tw/excel/how-data-journeys-through-excel), [外部資料範圍](https://support.microsoft.com/zh-TW/Excel/manage-external-data-ranges-and-their-properties) | 匯入, 匯出, 本機, 欄位, 儲存格與重新整理 |
| `microsoft-ports` | [Microsoft 伺服器網路連接埠](https://learn.microsoft.com/zh-tw/security-updates/security/20214371) | 通訊協定, IP 位址, 網域名稱與連接埠, 本詞表的 TCP / UDP port 採通訊埠 |
| `cisco-video` | [Cisco 視訊裝置使用者指南](https://www.cisco.com/c/dam/en/us/td/docs/telepresence/endpoint/ce910/Localization/UG/dx70-dx80-user-guide-ce910-zh_TW.pdf) | 視訊通話的用詞 |
| `user preference` | 本 setup 的使用者技術寫作要求 | 軟體串接, Git 儲存庫, 技術規格名稱與半形標點 |

## 新增詞條與套用

每筆規則的 `expected` 是建議用詞, `patterns` 或 `pattern` 是需提示的用法, `specs` 保存正例與應保留的反例, 會在 prh 載入時驗證. 可確定的詞彙使用字串, 依上下文決定的詞使用限定語境的 pattern. 每組詞條註明上表的來源 ID, 補詞時先確認詞義與開發用法, 再加入轉換與保留案例. 含其他規則的文字還須核對完整引擎的結果, 如回呼與函式的連續修正, 字串替換後不得留下可確認的簡體字. [prh 官方格式](https://github.com/prh/prh#prh-format)

```yaml
  - expected: 建議用詞
    patterns: [需提示的用詞]
    specs:
      - from: 需提示的用詞
        to: 建議用詞
```

修改 repo 來源後, 依既有 installer 的資產同步與備份流程套用到本機, 再以正例, 正確用詞與可能誤判的語境核對 lint / fix 結果. 先 lint 再檢視 fix, MCP 回傳修正內容, CLI 的 `--fix` 可能直接寫檔, 不將預覽當成已寫入原文
