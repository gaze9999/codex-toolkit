# Angular Checks 唯讀檢查

四項 Angular 與 Nx 的唯讀檢查共用同一個執行檔與輸出層, 結果可輸出文字, JSON, Markdown 與離線 HTML, 另有 `maintainability` 範圍限定的維護審查, 輸出自己的 JSON 報告

使用 Rust 1.89 以上的 stable 版本建置, 建置時需要同一份儲存庫內的 `tools/report-html`, 執行時只有 `--changed` 與 `change-impact` 需要 Git

```sh
cargo build --locked --release --manifest-path tools/angular-checks/Cargo.toml
angular-checks components customer --root /path/to/workspace --project customer-ui
angular-checks form-contract --root /path/to/workspace --contract forms.json --format json
angular-checks generator-preflight --root /path/to/project --identifier TXN001 --selector app-txn001
angular-checks change-impact --root /path/to/repository --format all --out /path/outside/report
angular-checks maintainability --root /path/to/project --scope src/feature --mode module --typescript /approved/typescript/lib/typescript.js --report /path/outside/review.json
```

| 指令 | 用途 | 結束碼 1 |
| --- | --- | --- |
| `components [關鍵字 ...]` | 盤點 Nx 工作區的元件: 專案, 類別, selector, custom element, 原始檔, 範本, 樣式, standalone, 說明 | 沒有符合的元件 |
| `form-contract --contract FILE` | 依欄位規格比對 TypeScript 的 form control 與範本的 `formControlName` | 有不符項目 |
| `generator-preflight --identifier ID` | 產生檔案前找出既有的 identifier 與 selector | 已有相同名稱, 加上 `--allow-existing` 時為 0 |
| `change-impact` | 列出已暫存, 未暫存與未追蹤的檔案, 以及檔案內出現的公開介面標記 | 不使用 |
| `maintainability` | 依明確範圍挑選檔案並記錄雜湊, 用已核准安裝的 TypeScript 與選用的 Angular compiler 執行 AST 規則, 寫出一份新的 JSON 報告, 規則與結果欄位見 [維護審查](../../skills/angular-development/references/maintainability-review.md) | 有機械性 FAIL |

輸入錯誤或環境問題的結束碼為 2, 訊息以 `error:` 開頭寫到標準錯誤, `--root` 省略時使用目前資料夾
同一個選項重複指定時回報錯誤, `components` 的關鍵字以 `--` 開頭時放在 `--` 分隔符之後, 例如 `components --root DIR -- --wide`
`maintainability` 必須指定 `--root`, 只有 `--file` 與 `--dependency` 可以重複, 不使用 `--format`, `--out` 等共用輸出選項
`--changed` 與 `change-impact` 需要 `--root` 位於 Git 儲存庫內

## 選項

| 選項 | 適用 | 內容 |
| --- | --- | --- |
| `--project NAME` | `components` | 只列出該 Nx 專案, 不分大小寫 |
| `--changed` | `components` | 只列出原始檔, 範本, 樣式有變更的元件, `component-mapping.ts` 變更時包含已註冊為 custom element 的元件 |
| `--limit N` | `components` | 報告內最多列出的筆數, 預設 50, 0 為全部, 摘要的總數不受影響 |
| `--selector NAME`、`--allow-existing` | `generator-preflight` | 另外檢查 selector, 有既有項目時仍以 0 結束 |
| `--format`、`--json`、`--out`、`--style-dir` | 全部 | 見下方 |

每次執行在標準輸出印出數行摘要, 最後是報告檔的路徑, 完整結果只寫入報告檔, 結果再多摘要長度也不變

| 選項 | 內容 |
| --- | --- |
| 省略 `--format` | 只寫入 `report.md` |
| `--format json,md,html` | 寫入指定的格式, 以逗號分隔, `md` 可寫成 `markdown`, `all` 代表三種 |
| `--out DIR` | 報告資料夾, 必須尚未存在且位於受檢查的目錄之外, 省略時使用系統暫存目錄下的新資料夾 |

`--json` 等同 `--format json`, 寫入檔案時結束碼仍反映檢查結果
HTML 與 Markdown 由共用的 [report-html](../report-html/README.md) 產生, `--style-dir` 可套用外觀套件

## 判讀範圍

- `components` 需要根目錄有 `nx.json`, 略過 `node_modules`, `dist`, `build`, `coverage`, `.angular`, `.nx`, 版本控制與虛擬環境資料夾, 以及 `.spec.ts`, `.test.ts`, `.d.ts`
- 元件以 `@Component` 與其後的 `export class XxxComponent` 辨識, 一個檔案可有多個元件, 說明取自裝飾器正上方的 JSDoc 區塊, 沒有時把類別名稱拆成單字
- custom element 讀取 `component-mapping.ts` 內 `{ selector: '...', component: Xxx }` 的寫法, 依匯入的檔案與類別名稱對應, 支援 `Original as Alias`, 經由 `index.ts` 轉出的匯入不解析
- `form-contract` 的欄位規格格式見 [forms.example.json](examples/forms.example.json), 可辨識 `name: new FormControl(...)`, `name: xxx.control(...)` 與 `name: [...]` 三種寫法
- `generator-preflight` 以不分大小寫的文字比對搜尋常見的原始碼與設定檔副檔名
- `change-impact` 的標記為 `selector:`, `@Input`, `@Output`, `CustomEvent`, `createCustomElement`, `component-mapping`, 屬於文字比對的候選
- 以上都是語法層級的比對, 動態組出的名稱, 執行期註冊與跨套件引用需要另外核對
