# Plugins

Plugin 由 `skills/` 的工作流程、`plugins/catalog.json` 的來源映射及 `plugins/ID/plugin.json` 的 metadata 組裝. `marketplace/plugins/` 是可直接使用的自含套件, 安裝入口見 [市集](marketplace.md)

## 功能與選用相依

| ID | Skills | 選用 runtime |
|---|---|---|
| `packaging-acceptance` | `packaging-acceptance`、`plugin-packaging` | 無 |
| `jev-evaluation` | `jev-evaluation` | `jev` |
| `documents-specifications` | `context-brief`、`doc-updater`、`local-document-processing` | `local-documents` |
| `environment-evidence` | `validation-evidence-review`、`test-strategy` | `workspace-inspection` |
| `frontend-engineering` | `angular-development`、`angular-member-order`、`react-development`、`vue-development`、`ui-ux-design`、`playwright-cli` | `playwright`、`serena`、`edge-devtools` |
| `agent-workflow` | `agent-governance`、`coding-prompt`、`task-routing`、`task-guide` | 無 |
| `multilingual-proofreading` | `multilingual-proofreading` | `textlint`、`cspell` |
| `local-activity` | `local-activity-query` | 無 |
| `project-documentation` | `readme-maintainer`、`license-maintainer` | 無 |

`runtime_profiles` 列出所屬 setup 的選用工具, 依任務另外設定 runtime、MCP 與帳戶. 文件與工作區 MCP 使用 `python-tools/` 的 versioned core. Plugin 的網站連到 [GitHub 來源](https://github.com/gaze9999/codex-toolkit)

前端 Plugin 收錄 [UI 需求與細節驗收](../skills/ui-ux-design/references/detail-review.md)、[Angular 排版與短寫](../skills/angular-development/references/angular-style.md)、[呼叫鏈與 Model 型別](../skills/angular-development/references/code-maintainability.md), 以及 [agent 參考索引](../agents/references/angular-style.md). 相同參考檔隨 Angular 獨立 Skill 自動收錄

即時表格的列身分、焦點、排序與暫停條件由 [UI 驗收參考](../skills/ui-ux-design/references/detail-review.md#streaming-tables-and-details) 說明. 環境與驗證證據 Plugin 收錄 [效能與串流量測](../skills/test-strategy/references/performance-and-streams.md), 區分來源收集、保存、傳輸與畫面更新, 按需選擇閒置、活動、大量更新與長時間診斷案例

## Skill 邊界與選擇性啟用

依實際用途選入口, references 只在需要該流程時載入, 不以安裝數量決定使用方式

Plugin 的收錄數量、已安裝 Skills、探索清單及單次任務實際啟用的 Skills 分別核對. 更新或精簡時依 [指示效益評估](../skills/agent-governance/references/component-authoring.md#evaluate-instruction-utility) 比較相符的任務與版本, 產物 hash 由封裝檢查核對, 實際載入及行為由目標用戶端驗證

| 需求 | 入口與條件 |
|---|---|
| 找既有抽出版、核對來源 hash | `$local-document-processing` 的 [唯讀來源比對](../skills/local-document-processing/references/source-matching.md) |
| 轉換文件或修改指定 Markdown | `$local-document-processing`, 分別核對來源、輸出與寫入授權 |
| 根據實作更新已指定文件 | `$doc-updater`, 有變更證據與具體目標, Notion 依明確指定的範圍操作 |
| 比較來源與已安裝 Skills / runtime | `$validation-evidence-review` 的 [環境比對](../skills/validation-evidence-review/references/environment-comparison.md), 不套用同步 |
| 檢視既有測試、建置或 UI 證據 | `$validation-evidence-review`, 保留來源版本與涵蓋, 不重跑命令 |
| 選擇或執行本次所需測試 | `$test-strategy`, 依變更與已授權範圍操作 |

平台或 SDK 專用 Skill 依專案實際技術與選定工具使用. Agent、React、環境變數或圖表等一般需求不會單獨決定 provider、Framework、代管服務或帳戶開通, 第三方 Plugin 沿用原廠更新來源, 選定工具後仍遵守其必要前置流程

## 來源與映射設定

| 欄位 | 意義 |
|---|---|
| `id` | Plugin 的來源 ID, manifest 名稱為 `codex-ID` |
| `status` | `ready` 可組裝, `blocked` 需有 `blocked_reason`, 明確選取會回報原因 |
| `skills` | 此 Plugin 收錄的 canonical Skills, 可為空清單以提供 MCP / app 組件 |
| `resources` | `{source, target}` 對應來源樹與套件內的目錄 |
| `components` | `{source, target}` 對應單一檔案與套件內的完整路徑 |
| `runtime_profiles` | 已存在於 setup 清單中的選用工具名稱 |

同一 Skill 在 catalog 中最多有一個 Plugin owner, 未加入 Plugin 的 Skill 仍可獨立使用. 可選組件包含 portable `mcp.json`、已註冊的 app mapping、hooks 與資產, app / hook JSON 的 entry point 由 `extensions.com.openai` 指定. 應用程式二進位檔使用獨立產品, 權限與帳戶依實際執行環境設定

檢查器拒絕路徑逃逸、連結、大小寫衝突、憑證 / 私密金鑰及未收錄的相對引用. VCS、venv、快取、測試輸出與暫存檔排除在產物外

## 檢查與建置

使用 Python 3.11+, 從完整 checkout 執行

```text
python -B mcp/scripts/prepare_plugin_release.py --check
python -B mcp/scripts/prepare_plugin_release.py --development --output dist/plugins-preview
python -B mcp/scripts/prepare_marketplace.py --write
python -B mcp/scripts/prepare_marketplace.py --check
```

`--check` 在記憶體檢查映射與引用, `--plugin ID` 只選取一組. 開發包使用 `--development`, 標記 `source_state: working-tree`. 不帶此選項的 ZIP 建置要求乾淨、已提交且受 Git 追蹤的來源

ZIP 使用固定 metadata 與排序, 暫存組裝後讀回全部成員與 SHA-256, 完整通過才寫到新的輸出目錄. 每組含 `plugin.json`、`LICENSE`、`source-manifest.json`、Skills 與選定資源. 組合 `codex-toolkit-plugins.zip` 含 `.agents/plugins/marketplace.json` 與 `plugin-release-manifest.json`

市集生成器依逐檔 hash 辨識可更新的副本, 來源或生成內容有獨立修改時停止受影響更新. `.github/workflows/plugin-release.yml` 在符合 [Plugin workflow 的實際門檻](../.github/workflows/plugin-release.yml) 的 Release 建置 ZIP 與 checksum, 手動執行依 workflow 設定處理指定來源. 整合產品操作見 [打包工具](operating-model.md)

## 已安裝 Plugin 更新

先核對市集的 `source_type`、已安裝 ID 與啟用狀態, Git 與本機來源使用不同更新入口

GitHub 市集使用已發布內容, 保留 Git 來源, 發布後更新市集並逐一更新選定 Plugin. 以下以 `codex-agent-workflow` 為例, 先確認目前 CLI 的 help, 停用或自訂設定需透過相容的原生管理介面保留

```text
codex plugin list --marketplace codex-toolkit --json
codex plugin marketplace upgrade codex-toolkit --json
codex plugin add codex-agent-workflow@codex-toolkit --json
```

既有本機市集可預覽並套用指定 working-tree 快照:

```text
python -B mcp/scripts/sync_local_plugins.py --plugin frontend-engineering
python -B mcp/scripts/sync_local_plugins.py --plugin frontend-engineering --apply
```

`sync_local_plugins.py` 只更新已註冊的本機市集, 不適用 GitHub 市集. `plugins --sync-installed` 是同一入口的 setup 別名. 初次安裝使用 [市集指令](marketplace.md), 不為套用未發布來源自動切換來源類型. 更新前保留備份與其他 Plugin 設定, 更新後核對內容與啟用狀態, 重新載入 Codex 再確認 Skill discovery 及需要的實際操作

活動摘要只讀取已在執行的 HTTP loopback monitor, 期間可用 `1h`、`24h`、`7d`、`all`, 未知值為 null. 回應限定為 metadata, 大小及連線時間有上限, 詳細資料格式見 [活動 Skill](../skills/local-activity-query/SKILL.md)
