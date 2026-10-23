# Toolkit 市集 MCP

提供公開 Toolkit 的 Plugin 目錄、Skills 搜尋與 Markdown 讀取, 透過 Streamable HTTP 供網頁版加入

## 工具

| 工具 | 用途 |
|---|---|
| `list_plugins` | 列出 Plugin 版本與 Skills 成員 |
| `search_skills` | 依英文關鍵字或 ID 搜尋, 支援分頁 |
| `read_skill` | 讀取選定 Skill, 回傳來源提交、SHA-256 及參照清單 |
| `read_skill_reference` | 讀取同版本的 Markdown 參照 |

原 Git 市集維持 Plugin 安裝用途, MCP 提供工作流程文字, 不註冊原生 Skills 或執行其中的 scripts

## 本機建置與驗證

需要 Node.js 24 與完整 Toolkit Git checkout, 在本目錄執行:

```sh
npm ci --ignore-scripts
npm run snapshot
npm test
npm start
```

啟動前須提供下方 WorkOS 環境變數, 測試使用隔離簽章 fixture, 不需要正式帳號

本機端點為 `http://127.0.0.1:8787/mcp`

快照只讀取目前 HEAD 的 `plugins/catalog.json`、對應 manifest 與 `skills/` 下已提交的 SKILL.md / references Markdown, 不讀取工作樹內容、私人 Setup、Global、公司資料或用戶端快取
`data/catalog.json` 為生成內容, 不提交 Git, 更新來源提交後須重新生成並部署

## 部署

使用獨立 Vercel 專案, Node.js 24、無框架、安裝指令 `npm ci --ignore-scripts --no-audit --no-fund`, 無額外建置指令

部署檔案限於 `package.json`、`package-lock.json`、`vercel.json`、`catalog.mjs`、`handler.mjs`、`auth.mjs`、`api/mcp.mjs`、`api/oauth.mjs`、`data/catalog.json` 與 Toolkit 根目錄 LICENSE
不將整個 checkout、node_modules 或其他本機檔案上傳
端點為部署主機的 `/mcp`, 內容來自公開 Toolkit, 存取採 WorkOS OAuth 與單一使用者限制

部署後執行:

```sh
node scripts/verify-remote.mjs https://YOUR-HOST/mcp
```

驗證器預設以本機 data/catalog.json 為預期快照, 可用第三個命令列參數指定候選快照, 核對預期提交、Plugin 目錄、兩份代表性文件的完整分頁、實際內容與 SHA-256, 並檢查四項工具及路徑拒絕, 不將舊版本可回應視為更新成功
驗證前由 MCP_ACCESS_TOKEN 環境變數供應已核准的存取權杖, 驗證器不取得或刷新權杖, 不跟隨重新導向, 不將權杖列入命令列或輸出
驗證器亦核對匿名拒絕、OAuth 探索與來源/快照靜態路徑不可下載
網頁版加入後另確認實際對話可呼叫工具

## 請求診斷

HTTP 入口回傳 `x-mcp-request-id`, 由伺服器產生 UUID, 記錄請求收到、完成或中斷, 包含處理階段、白名單方法與工具名稱、HTTP 狀態、耗時、回應位元組數及 JSON-RPC 錯誤碼
不記錄 Authorization、Cookie、使用者身分、用戶端提供的請求 ID、工具參數、文件內容、例外訊息或堆疊, 診斷輸出失敗不改變請求結果

對照同一部署與 UTC 時段的用戶端錯誤及服務端記錄, 先區分沒有收到請求、認證拒絕、處理例外、HTTP 回應與用戶端轉換, 缺少歷史記錄不能排除任一層
重試成功只證明該次呼叫完成, 間歇性錯誤須保留原始結果與尚未確認的原因
認證程序意外拋錯回傳 503, MCP 處理或回應讀取例外回傳 500, 輸入串流失敗回傳 400 或保留已中斷連線, 不輸出原始例外內容

參考 [Vercel Function Logs](https://vercel.com/docs/functions/logs)

## 網頁版加入

1. 開啟 ChatGPT Plugins, 選擇 Add custom MCP server
2. 輸入名稱與部署的 Server URL, 選擇 OAuth、CIMD 與 PKCE S256, 依探索結果使用 none 用戶端認證
3. 建立並安裝 Plugin, 在新對話以 @ 選取
4. 請它先搜尋 Skill, 再讀取 SKILL.md 與任務需要的參照, 有 nextOffset 時繼續讀取

參考 [OpenAI 加入方式](https://developers.openai.com/api/docs/guides/custom-mcp-server) 與 [Vercel MCP 部署](https://vercel.com/docs/mcp/deploy-mcp-servers-to-vercel)

## WorkOS AuthKit 設定

此服務是 OAuth 資源伺服器, 使用 WorkOS Connect 簽發的 RS256 存取權杖, 每次 MCP 請求核對簽章、issuer、audience、有效期限、固定使用者 sub 與 openid scope
openid 表示登入授權, 本服務的存取權限由固定 sub 與 MCP audience 決定, 不把登入成功視為允許所有使用者
缺少設定回傳 503, 未登入或無效權杖回傳 401, 非指定帳號或缺少 scope 回傳 403

在 Vercel Production 設定下列環境變數, 本機啟動時亦由程序環境提供:

| 變數 | 內容 |
|---|---|
| WORKOS_ISSUER_URL | AuthKit 的 HTTPS issuer, 不含結尾斜線, 必須與公開探索結果完全一致 |
| MCP_RESOURCE_URL | 正式 MCP HTTPS URL, 與 WorkOS Resource Indicator 完全一致 |
| MCP_ALLOWED_SUBJECT | WorkOS 應用程式使用者的完整 ID, 對應權杖 sub |

WorkOS 管理帳號與應用程式使用者是不同身分, 必須由應用程式登入後確認 sub
不要把密碼、權杖或 API Key 放入儲存庫、命令列或對話

1. 在 WorkOS Production 的 Connect > Configuration 啟用 CIMD, DCR 保持關閉
2. 加入 MCP_RESOURCE_URL 作為 Resource Indicator, 不使用萬用字元
3. 啟用所需的個人登入方式, 使用 AuthKit 預設網域, 不需企業 SSO 或自訂網域
4. 核對公開探索的 CIMD、PKCE S256、issuer 與 JWKS, 由 ChatGPT 實際完成 CIMD 授權及權杖交換
5. 確認核准帳號的使用者 ID, 設定 MCP_ALLOWED_SUBJECT, 保存 Vercel 變數後重新部署
6. 驗收未登入拒絕、本人四項工具可用、非本人拒絕及重新連線, 另檢查舊部署網址是否仍可匿名存取

CIMD 用戶端預設使用標準 OAuth scopes, 不要求未配置的自訂 read:toolkit scope
自動驗證使用另外核准的權杖供應方式, 不從瀏覽器或 ChatGPT 擷取登入權杖, 不預設開放 Machine-to-Machine 身分

參考 [OpenAI MCP 認證](https://developers.openai.com/plugins/build/auth)、[WorkOS MCP](https://workos.com/docs/authkit/mcp) 與 [WorkOS 權杖欄位](https://workos.com/docs/authkit/connect/token-claims)


## Git 市集與 Private MCP 同版本更新

桌面使用原生 Git 市集 Plugin, Cloud 與 Web 使用經 OAuth 認證的 Private MCP, 兩種入口共用同一個完整 Toolkit commit 作為更新目標
Plugin 版本、MCP 服務版本與 Toolkit 來源 commit 分開核對, Plugin 版本號相同不代表內容相同

1. 從已發布的公開來源選定完整 commit, 在私人還原 profile 記錄目標, 保留上一個已驗收 commit 與部署 ID
2. 在隔離 checkout 取得該 commit, 檢查生成的 Plugin 分發內容與正式 Skills, 以同一 commit 產生 MCP 快照並執行測試, 不讀取開發工作樹的未提交內容
3. 使用原生市集更新已選 Plugin, 不複製快取或覆寫使用者自訂檔案, 核對實際安裝、啟用狀態與下方檔案比對, 上游在更新期間前進時重新選定共同目標, 不把不同提交視為完成
4. 桌面檔案符合後, 以已驗證服務程式與同一公開快照部署 MCP, 保留 OAuth、單一使用者限制及部署保護, 不隨快照更新升級服務程式或相依套件
5. 以候選快照執行 verify-remote, 或在已認證 Private MCP 逐一呼叫四項工具, 核對共同 commit、Plugin 目錄及代表文件完整內容與 SHA-256, 同時檢查匿名拒絕與 OAuth 探索
6. 桌面重新載入後驗收 Skill discovery 與代表操作, Cloud 和 Web 分別確認實際對話能探索及呼叫 Private MCP, 平台間不互相代替驗收
7. 全部適用項目通過後才把共同目標記為已驗收, 部分失敗記錄各端實際版本並停止後續自動更新, 以原生支援的還原流程處理, 不覆寫快取或改寫 Git 歷史

在本目錄執行唯讀桌面檔案核對:

```sh
node scripts/verify-desktop.mjs TOOLKIT_REPO MARKETPLACE_CACHE data/catalog.json EXPECTED_FULL_COMMIT
```

MARKETPLACE_CACHE 指向該 Git 市集的快取根目錄, 下層為 Plugin ID / version, 由目前用戶端實際安裝位置取得
此命令核對快照來源及每個 Plugin 在目標提交的完整分發檔案, 缺少檔案、內容差異或額外檔案均以非零狀態結束, 不寫入快取
它驗證快照所列的所有 Plugin, 僅安裝部分 Plugin 的用戶端須保留缺項結果, 不據此自動安裝其他 Plugin
原生安裝狀態與執行中用戶端載入另由用戶端驗收, 快取內容相同不代表已啟用

排程使用同一流程與共同目標, 缺少桌面原生更新入口、認證工具或已審查服務基線時只檢查差異並通知必要操作, 不單獨推進 MCP
不從瀏覽器擷取權杖, 不把人工對話 OAuth 成功視為無人值守權杖刷新已可用
