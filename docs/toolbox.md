# 三類工具整合目錄

`tooling/toolbox.py` 從正式來源產生 Skills、連接器與外掛程式三類目錄, 支援 Codex 與 Claude 的 manifest
既有 Plugin 分組保持原樣, 獨立 Skills 產生各自的單一 Skill 外掛, 各資料夾都由相同來源生成

## 公開來源

從 Toolkit 根目錄執行:

```sh
python -B tooling/toolbox.py plan
python -B tooling/toolbox.py prepare --output .tmp/toolbox-public
python -B tooling/toolbox.py verify --output .tmp/toolbox-public
```

`plan` 回傳來源與分類, `prepare` 寫入新的資料夾, `verify` 核對完整檔案清單與 SHA-256
產生器保留現有輸出, 修改來源後使用新的 output 路徑
此流程準備來源目錄, 安裝、ZIP、帳戶登入、部署與發布由各自的操作處理

## 私人選擇

指定私人 root 與 audience:

```sh
python -B tooling/toolbox.py plan --private-root /path/to/private-source --audience personal
python -B tooling/toolbox.py prepare --private-root /path/to/private-source --audience private --output .tmp/toolbox-private
```

私人 root 需要 `profiles/personal-toolbox.json`, 欄位如下:

| 欄位 | 用途 |
| --- | --- |
| `schema_version`、`name`、`version`、`owner`、`repository` | 整合目錄格式、識別與來源 |
| `selection_source` | 同 root 的 JSON, 包含完整 `toolkit_revision`、`skills` 與 `plugins` 選擇 |
| `toolkit_revision` | 選用的整合包完整來源提交, 與一般還原選擇的 Toolkit pin 分開管理 |
| `connector_inventory` | 已去除機敏值的盤點 JSON, 包含 `mcp_servers` 與 `plugins` |
| `private_bundles` | 同 root 的 bundle JSON, 沿用既有 `manifest_source`、`skills`、`resources`、`components` 與 `runtime_profiles` |
| `private_skills` | 含 SKILL.md 的獨立私人 Skill 相對資料夾 |
| `integration_source` | 選用的私人整合 profile, 明確選擇 MCP 宣告、工具資源與整合外掛版本 |
| `publication` | 選用的私人 Git 市集 URL、已核對 repo ID、工作規範來源及 ZIP 暫緩設定 |

`public` 只選公開 Toolkit 來源, `private` 選私人工作流與連接器參考, `personal` 合併已審查的公開選擇與私人項目
整合包的完整 Toolkit 提交必須與 checkout HEAD 相同, 未另指定時沿 selection_source 的 pin, 工作樹差異另記為 working-tree
連接器輸出只採用名稱、owner、傳輸類型、盤點啟用值及憑證環境變數名稱, 實際載入與認證維持未知狀態

私人整合另可執行 `publication-plan`, 回傳 Git 市集與 Release 的分工及尚待核對的條件
此唯讀操作使用 profile 的 `publication.candidate_repository`, `repository_state` 為 `verified-private` 時須保存實際讀回的正整數 `repository_id`
`archive_policy` 目前為 `deferred`, 個人維護入口可透過 `instructions_source` 指定要產生到根目錄 AGENTS.md 的正式來源
產生目錄包含 `* -text` 的 .gitattributes, 保留來源位元組與雜湊, `verify` 將根目錄 Git metadata 與散布檔案分開核對

## 平台串接

| 入口 | 產生內容 | 目的端操作 |
| --- | --- | --- |
| Skills | `skills/README.md` 與來源、版本、單一 owner 對照 | 依用途讀取各 Plugin 內的 SKILL.md |
| 連接器 | `connectors/README.md` 與篩選後的參考資料 | 依正式安裝方式準備 runtime、資料 roots 與登入 |
| 外掛程式 | `plugins/`、Codex 市集與 Claude 市集 manifest | 加入本機市集, 或準備單一外掛的上傳版本 |

個人工作規範是按需載入的 Skill, 常駐規範由平台支援的設定入口套用
各平台能讀取的元件與本機工具能力不同, 實際安裝、探索、登入及代表操作各自驗收
Claude 的格式及上傳方式依 [外掛說明](https://claude.com/docs/plugins/overview)、[平台能力](https://claude.com/docs/plugins/build#check-what-each-app-loads) 與 [manifest 規格](https://code.claude.com/docs/en/plugins-reference)

## MCP 與執行資源

整合 profile 使用 schema_version、owner、plugins 與 files, 每個 plugins 項目指定 name、version、setup、resources 與 connectors
resources 明確指定 toolkit / private owner、來源相對路徑與套件內 target, 不讀 installed cache 或相鄰 checkout
relocations 可將參考入口移出平台會探索 Agent 的資料夾, 保留位元組、來源及相同路徑深度, 避免改變相對連結
requires_plugin 讓已有工作流的整合只套用到已選外掛, 額外連接器可以沒有 Skill
來源元件版本保存在 source_version, 整合產物版本由該私人 profile 管理

connectors 的 server 使用已核對的 Claude MCP 宣告, user_config 保存目的端輸入欄位, runtime 宣告來源專案、相依套件與版本檢查
產生器輸出 Claude 的 .mcp.json 與 Codex 的 mcp.json, 本機 Codex 入口從裝置設定解析需要的值, 不依賴 Claude userConfig
遠端入口使用固定 HTTPS URL, 只允許經選取的非機敏標頭, 不輸出原裝置認證

runtime/setup.py 的 list / plan / doctor 是唯讀檢查, install 僅準備明確選定元件的新環境
Python 建置來源先複製到環境內的 .sources, 不讓套件建置改寫外掛原檔, 既有環境及不完整安裝均保留
安裝不修改 Codex 或 Claude 設定, server 啟動不安裝相依套件, 目的用戶端載入與操作另行驗收

依 [OpenAI Plugin 格式](https://developers.openai.com/plugins/build/plugins) 與 [Claude manifest](https://code.claude.com/docs/en/plugins-reference) 維護兩個 adapter, 個人選擇與裝置值保留在私人 owner
