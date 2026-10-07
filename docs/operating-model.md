# 工作流程、打包與評估工具

## 功能與資料來源

| 來源 | 用途 |
|---|---|
| `skills/` | 可獨立使用的工作流程, `SKILL.md` 提供啟用條件, references、scripts、assets 依用途載入 |
| `plugins/catalog.json` | Plugin 分組、Skill 清單、選用 runtime 與資源映射 |
| `plugins/ID/plugin.json` | Plugin 名稱、版本、說明、網站與相容用戶端的顯示設定 |
| `agents/` | 選用的通用工作規範與 Angular 參考索引 |
| `python-tools/` | 可獨立執行的 CLI 與 versioned document / workspace core |
| `mcp/` | 共用核心的 MCP adapters、安裝器、相依設定與建置工具 |
| `tooling/products.json` | 產品來源、建置類型、預設選取與必要相依 |
| `evals/routing.json` | positive、negative、collision 路由案例及預期選用的 Skills |
| `evals/benchmark.json` | before / after 比較使用的固定任務 ID 與驗收條件 |

同一 Skill 可獨立安裝或隨 Plugin 使用, 在同一用戶端選定單一啟用來源. Plugin 內的 Skill 來源由 catalog 生成, 內部引用及來源 hash 在打包時核對

## UI 與程式碼工作流程

`frontend-engineering` 包含 Angular、React、Vue、UI/UX 與 Playwright Skills. `ui-ux-design` 對照原始需求及有效補充, 操作實際介面, 檢查畫面、顯示資料、互動、窄畫面與必要的錯誤 / 載入狀態, 修正後重測. 無法連到目標時, 列出受影響需求與缺少的執行環境

Angular 範例提供責任分組、響應式排版、單 statement `if`、提早 return、`??=` / `||=`、數字顯示與 TypeScript `extends` / `Pick` / `Omit`. 採用前核對版本、運算語意與資料精確度, 完整內容見 [排版與短寫](../skills/angular-development/references/angular-style.md)、[呼叫鏈與型別](../skills/angular-development/references/code-maintainability.md)

Jev 在已核准資料需要語意排序或有限 rubric 比較時選用, UI 的像素、資料綁定與互動以瀏覽器及資料來源核對. Jev 的帳戶與操作見 [使用說明](usage/jev.md)

## 產品設定與建置

使用 Python 3.11+ 及 Git, 從完整 Toolkit checkout 執行

```text
python -B tooling/package.py plan
python -B tooling/package.py build --version 0.2.0 --output dist/local-preview
python -B tooling/package.py verify --output dist/local-preview
```

預設產品是 `plugins`、`skills`、`governance` 與 `application-source`. `governance` 收錄通用 agent 範例, `application-source` 包含 Setup CLI、Python 工具、MCP adapters、requirements、文件與授權

| 欄位 / 選項 | 意義 |
|---|---|
| `id` | 可用 `--product` 選取的唯一產品名稱 |
| `kind` | `source`、`plugins`、`mcp` 或 `native`, 決定組裝入口 |
| `default` | 未指定產品時是否選取 |
| `sources` / `strip_prefix` | source 產品的明確來源與 ZIP 路徑前綴 |
| `requires` | 該產品的 runtime、平台或建置相依 |
| `--product ID` | 明確選取產品, 可重複指定 |
| `--version` | 整包版本, 個別 Skill / Plugin 版本由各自 metadata 保存 |
| `--release` | 要求完整、已提交且乾淨的來源, 所有封裝來源必須受 Git 追蹤 |
| `--python` | `portable-cli` 使用的原生 standalone Python, 版本依 CLI release requirements |

`mcp` 使用 wheel / installer builder, `portable-cli` 使用 CLI native builder. 建置需要各自 requirements 中的固定套件及必要網路存取, CLI 原生包在 Windows / macOS 的支援 runner 建置

輸出使用新的目錄, ZIP 保持固定時間與排序, 先完成暫存組裝、內容及 SHA-256 核對後才提升完整輸出. `package-manifest.json` 記錄產品、產物大小及 hash. 來源 manifest 的 `working-tree` 表示開發內容, `committed` 表示乾淨已提交來源, `base_revision` / `source_revision` 保存基底提交, 逐檔 hash 定位封裝內容

## 來源盤點與路由觀察

```text
python -B tooling/evaluate.py inventory
python -B tooling/evaluate.py routing
python -B tooling/evaluate.py routing --observed /path/to/observations.json
python -B tooling/evaluate.py compare --runs /path/to/runs.jsonl
```

`inventory` 回傳 Skill 的 UTF-8 metadata / body bytes、reference / script 數與 Plugin owner, 獨立 Skill 的 `plugin` 為 null

`routing` 未提供 `--observed` 時檢查案例格式與 Skill 名稱, 回傳 `fixtures_validated`. 觀察檔是 JSON array, 每項含 `case_id` 與實際 agent 選用的 `selected` 清單. 評分回傳缺少 / 多選的 Skills 與未觀察案例, 全部案例符合才回傳 `passed`

## before / after 資料欄位

JSONL 每行保存一項實測, 輸入只接受下列欄位, 不接受 prompt、原始 log、檔案內容或憑證

| 欄位 | 格式與意義 |
|---|---|
| `case_id` | benchmark 中的任務 ID |
| `trial` | 大於 0 的整數, 同 case / trial 的 before 與 after 配對 |
| `variant` | `before` 或 `after` |
| `model`、`effort`、`environment` | 最長 80 字元的識別標籤, 使用英數字、點、底線或連字號 |
| `source_revision` | 40 或 64 位小寫 hex revision |
| `accepted`、`first_pass` | boolean 或 null, 分別表示驗收通過及首次通過 |
| `validation` | `passed`、`failed`、`not_run`、`blocked` 或 null |
| `duration_seconds` | 非負有限數值, 單位為秒 |
| `input_tokens`、`output_tokens` | 非負整數或 null, 使用可取得的實測用量 |
| `context_bytes` | 非負整數或 null, UTF-8 byte 數, 保留其原始單位 |
| `tool_calls`、`subagents`、`retries`、`human_corrections`、`regressions` | 非負整數或 null, 分別記錄呼叫、worker、重試、人工修正及回歸問題數 |

比較僅使用共同 case / trial 且雙方都有值的欄位, 數值回傳 median, boolean 回傳已觀察成功率. 缺值保留 null, 輸出另列未配對資料、未觀察案例、條件差異與缺少的條件. 比較時固定初始材料、任務、驗收及環境, 每次只改一個變因
