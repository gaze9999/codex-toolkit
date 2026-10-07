# CLI 安裝與管理

## 四類設定入口

從儲存庫根目錄執行, Windows 使用 `launch-cli.cmd` 或 PowerShell 的 `./launch-cli.ps1`, macOS / Linux 使用 `sh launch-cli.sh`

```powershell
.\launch-cli.cmd --list
.\launch-cli.cmd agents --list
.\launch-cli.cmd agents global
.\launch-cli.cmd agents global --install --replace
.\launch-cli.cmd agents desktop
.\launch-cli.cmd agents subagent-profile --apply
.\launch-cli.cmd skills --list
.\launch-cli.cmd skills agent-governance
.\launch-cli.cmd skills agent-governance --apply
.\launch-cli.cmd plugins --list
.\launch-cli.cmd plugins jev-evaluation
.\launch-cli.cmd mcp --list
.\launch-cli.cmd mcp edge-devtools
```

Agents / Skills 清單使用確切名稱選取項目, Global 安裝與 Skills 同步保留預覽、衝突檢查及備份, Skills 的 `--apply` 需確認, 自動執行可在選定項目已獲授權時加 `--yes`. `agents desktop` 產生合併片段, 依[工作規範設定](../agents.md)處理既有 config.toml. Plugins 清單呈現來源批次、可用性與本機設定, 指定 ID 可預覽版本、來源映射與 hash, 安裝與帳戶連接使用 Codex 官方入口, 詳見 [Plugins](../plugins.md)

既有 `tool`、`bootstrap`、`check`、`update`、`uninstall`、`desktop`、`audit` 仍可使用, 原平台實作位於 `mcp/scripts/launch/`, 說明使用 `ACTION --help`

## 本機 MCP 安裝與獨立部署

`codex-toolkit` 維護公開 MCP 與安裝工具, Local Documents 以核心及 server 兩個 wheel 部署, 安裝後使用不依賴儲存庫 checkout

| 元件 | 原始碼 | 部署方式 |
| --- | --- | --- |
| `my-py-document-core` | 本 repo `python-tools/` | 安裝 versioned wheel, 公開 API 為 `my_py_document_core`, 目前 API 1 |
| `codex-local-documents-mcp` | 本 repo `mcp/mcp_servers/local_documents/` | 安裝 server wheel, 使用模組或 console command 啟動 |
| `my-py-workspace-core` | 本 repo `python-tools/` | 安裝 versioned wheel, 公開 API 為 `my_py_workspace_core`, 目前 API 1 |
| `codex-workspace-inspection-mcp` | 本 repo `mcp/mcp_servers/workspace_inspection/` | 唯讀查詢驗證證據與環境差異 |
| Jev | 本 repo `skills/jev-evaluation/` | `codex-jev-mcp` wheel 與相容 Skill installer, 可獨立部署 |

核心 wheel 從同一份 CLI 原始碼建置 namespaced package, MCP 不另維護一份核心, MCP runtime 使用已安裝的套件, 不修改 `sys.path` 來匯入另一個 working tree, 不保留 CLI repo 路徑

## Baseline 快速安裝

[統一安裝與監看說明](cli.md) 提供預設位置, 本機 wheel bundle, read roots, preview/apply 與環境沿用, 使用 `launch-cli.cmd bootstrap --apply` 或 `sh launch-cli.sh bootstrap --apply`, 不必逐一填 core/server wheel 路徑, 未設定 roots 的新工具先列 pending

## 任意位置部署 Local Documents

準備 `my_py_document_core-0.2.0-py3-none-any.whl` 與 `codex_local_documents_mcp-0.2.0-py3-none-any.whl`, 在使用者選擇的位置建立 Python 3.11+ 環境, 首次安裝公開相依套件需網路或對應平台的本機 wheel cache

Windows 範例, 請換成該電腦的真實路徑:

```powershell
python -m venv C:\path\document-runtime
C:\path\document-runtime\Scripts\python.exe -m pip install C:\path\wheels\my_py_document_core-0.2.0-py3-none-any.whl C:\path\wheels\codex_local_documents_mcp-0.2.0-py3-none-any.whl
C:\path\document-runtime\Scripts\python.exe -m pip check
```

macOS/Linux 使用 `/absolute/document-runtime/bin/python` 與對應路徑, 不直接搬移既有 virtual environment, 在新環境重新安裝

其他 MCP client 的 stdio 設定可使用:

```json
{
  "command": "/absolute/document-runtime/bin/python",
  "args": ["-I", "-B", "-m", "mcp_servers.local_documents.document_server", "--read-root", "/absolute/documents"]
}
```

Windows 的 command 換成 `C:\path\document-runtime\Scripts\python.exe`; `-I` 排除目前工作目錄與 `PYTHONPATH` 對套件來源的影響, 各 client 的設定格式自行依實際支援核對, 上述只有 command 與 args

也可使用環境中的 `local-documents-mcp --read-root /absolute/documents`, server 會等待 MCP JSON-RPC stdin, 由支援 stdio 的 client 管理程序

## 註冊到 Codex, 不需要 repo

在已安裝兩個套件的 Python 環境執行, 需已有使用者 Codex `config.toml`, 預設由 `CODEX_HOME` 或 `~/.codex` 定位, `--config` 可指定實際位置

```text
python -I -B -m mcp_servers.local_documents.install_document_mcp --read-root /absolute/documents
python -I -B -m mcp_servers.local_documents.install_document_mcp --read-root /absolute/documents --apply
python -I -B -m mcp_servers.local_documents.verify_document_mcp
```

第一行只預覽, `--apply` 才備份並更新 `local_documents` 設定, 其他設定保留, 重複相同設定回傳 unchanged, 預設 Python 是目前 interpreter, 必要時可用 `--python` 明確指定

每個讀取範圍分別提供 `--read-root`, 都必須是存在的絕對路徑, 預設不允許寫入, 需要時另加 `--write-root /absolute/output`, 不因 preview 或模型呼叫自動放寬範圍

三個 console command 分別是 `local-documents-mcp`, `local-documents-register`, `local-documents-verify`, 使用環境的絕對執行檔或 Python 模組方式, 不依賴 shell 選到哪個 Python

## 從 codex-setup 統一管理

已有 runtime 時, 可從本 repo 的入口註冊與驗證, 不必指定另一個 repo:

```text
python mcp/scripts/install_mcp.py local_documents --python /absolute/document-runtime/bin/python --read-root /absolute/documents
python mcp/scripts/install_mcp.py local_documents --python /absolute/document-runtime/bin/python --read-root /absolute/documents --apply --verify
```

首次建立 runtime 時提供兩個 wheel:

```text
python mcp/scripts/install_mcp.py local_documents --runtime /absolute/document-runtime --core-wheel /absolute/wheels/my_py_document_core-0.2.0-py3-none-any.whl --server-wheel /absolute/wheels/codex_local_documents_mcp-0.2.0-py3-none-any.whl --read-root /absolute/documents --apply --verify
```

- 預設或 `--dry-run` 只顯示 plan 與 wheel metadata/SHA-256, 不建立環境, 安裝套件或寫檔
- `--core-wheel` 與 `--server-wheel` 可更新各自套件, 先核對 wheel 名稱與內容, 不使用 editable install
- 新 runtime 必須提供兩個 wheel, 已存在的非 virtual environment 目錄會被拒絕, runtime 不放進本 repo
- `--apply` 先安裝明確提供的 wheel, 檢查套件相容性, 再呼叫 runtime 內的 guarded installer
- `--verify` 驗證 stdio discovery, 六種原生格式, 抽出版定位, OCR 與 Markdown 防護, 只使用臨時 fixture

原 `--documents-repo`, server 的 `--tools-root` 與 `python -m mcp_tools.*` 入口已退休, 舊版需重新安裝套件並註冊, 新設定使用已安裝模組, 不包含 repo 的 server.py 路徑

## 建置與版本

核心建置方式見 [核心建置指引](../../python-tools/docs/python-document-core.md), 本 repo 的 server wheel 可在具備 setuptools/wheel 的 Python 環境建置:

```text
python -m pip wheel --no-deps --no-build-isolation --wheel-dir /absolute/wheels .
```

目前 Local Documents server 固定使用 `my-py-document-core==0.2.0`, Workspace Inspection 新版來源固定使用 `my-py-workspace-core==0.2.0`, 並要求各自的 `API_VERSION=1`, 核心公開參數, 回傳資料或錯誤語意有變更時, 先檢查相容性再更新相依套件, 每個 MCP 可使用自己的相容版本與獨立環境. 新版來源與套件發布、runtime 安裝分開處理, 既有環境需更新後才能比較 current baseline

## Workspace Inspection

此 server 只有 `workspace_status`, `validation_evidence`, `compare_environment` 三個唯讀工具, 不執行同步, 安裝, build, test 或 Git 寫入

```text
python mcp/scripts/install_mcp.py workspace_inspection --runtime /absolute/workspace-runtime --core-wheel /absolute/wheels/my_py_workspace_core-0.2.0-py3-none-any.whl --server-wheel /absolute/wheels/codex_workspace_inspection_mcp-0.2.0-py3-none-any.whl --read-root /absolute/workspaces --apply --verify
```

已存在 runtime 時可改用 `--python`, 每個 `--read-root` 都必須是存在的絕對資料夾, 工具只能讀取其下路徑, 環境比對預設排除 `.env`, credentials, private key, VCS 與 cache, 詳細開發介面見 [Workspace Inspection MCP](../../mcp/mcp_servers/workspace_inspection/README.md)

修改或搬移原 repo 不會直接改變已安裝 runtime, 更新以 wheel 與 hash 為單位, 不用跨 repo source path 或 submodule working tree 當作啟動相依

## Jev

保留既有 Skill installer 的備份, credentials 與驗證流程, 統一入口預設只預覽, `--apply` 才安裝, 其他參數直接傳給既有 installer

```text
python mcp/scripts/install_mcp.py jev
python mcp/scripts/install_mcp.py jev --apply
python mcp/scripts/install_mcp.py jev --apply --replace --verify-online
python mcp/scripts/install_mcp.py jev --help
```

安裝位置可使用 `--skill-root`, `--runtime` 與 `--config` 指定, 組合包中的 Jev Skill installer 不需要完整 repo, 詳見 [Jev 安裝文件](../../skills/jev-evaluation/README.md)

`--verify-online` 以內建公開範例呼叫 Jev API, 未指定時沿用離線 MCP 驗證, 不把私人專案內容當作驗證資料

## 操作與驗證

- [Local Documents 操作教學](../usage/local-documents.md)
- [Jev 操作教學](../usage/jev.md)
- [Local Documents 開發驗證](../../mcp/mcp_servers/local_documents/README.md)

註冊後重新載入支援 MCP 的 client, 再核對工具清單, installer 或獨立 stdio 驗證通過, 不代表目前對話已 reload

這是 stdio 部署, 遠端 HTTP endpoint 需另行選擇 transport, authentication 與 host, Windows/macOS/Linux 的 native 相依需依平台安裝, 實機支援範圍以驗證結果為準

## Baseline MCP 與本機監看安裝

統一入口以 `mcp/mcp_servers/presets/baseline.json` 為準, 管理 server 清單, wheel 版本, tool 清單與選用項目, `codex-toolkit` 是公開維護來源, 安裝後 runtime 不依賴 checkout 路徑

## 使用者操作

需要 Python 3.11+ 與相符的本機 bundle, 首次安裝平台相依需網路或事先準備的 wheel cache, 不複製另一台電腦的 virtual environment

Windows 執行 `launch-cli.cmd bootstrap`, macOS / Linux 執行 `sh launch-cli.sh bootstrap`, 預設只預覽, `--apply` 才安裝與註冊

```powershell
.\launch-cli.cmd bootstrap
.\launch-cli.cmd bootstrap --apply
.\launch-cli.cmd bootstrap --read-root C:\path\approved-documents --apply
```

```sh
sh launch-cli.sh bootstrap
sh launch-cli.sh bootstrap --read-root /absolute/approved-documents --apply
```

也可使用 `python mcp/scripts/install_mcp.py bootstrap` 或 `python mcp/scripts/bootstrap_mcp.py`, 原 `install_mcp.py local_documents`, `workspace_inspection` 與 `jev` 參數仍保留

| 項目 | 預設處理 |
| --- | --- |
| Jev | 安裝 `codex-jev-mcp` wheel, 保留憑證優先順序, Key 缺少只列 pending setup, 不自動呼叫付費 API |
| Local Documents | 使用既有 core + server wheel, 新安裝只提供 read roots, 未指定則 pending roots, 既有 read/write roots 保留 |
| Workspace Inspection | 同樣需明確 read roots, 未提供時保留未設定, 不開放 cwd, home 或整台電腦 |
| OpenAI Docs | 官方唯讀 HTTP endpoint, 相同 endpoint 或 enabled plugin 已提供時沿用, 不建立第二份 |
| Context7 | 只有 `--context7` 才新增 hosted HTTP server, 使用 `/mcp` 的匿名額度, OAuth 先改用 `/mcp/oauth` 再 login, 詳見開發工具接法 |
| 既有 node_repl | 保留原設定, 不轉成 Python wheel, 不換 runtime |

已有同名但無法辨識來源的 server 會標示 conflict 並保留, 既有停用的同名 HTTP provider 保持停用, 不改動 plugin 或 AGENTS. GitHub, browser, Notion 等能力依實際用途另行設定

[開發工具接法](../tools/development.md) 提供 Playwright CLI + Skills / MCP, RTK 與工作台的獨立安裝方式, RTK / cmux adapter wheel 隨 release 提供, 由各工具的獨立安裝流程處理

## 路徑與非機敏設定

- 使用者 config: `$CODEX_HOME/config.toml`, 或 `~/.codex/config.toml`; `--config` 可指定
- 新 Windows runtime: `%LOCALAPPDATA%/codex-setup/mcp/<server>/`; `LOCALAPPDATA` 無效時使用使用者的 `AppData/Local`
- 新 macOS runtime: `~/Library/Application Support/codex-setup/mcp/<server>/`
- 新 Linux runtime: 絕對 `$XDG_DATA_HOME/codex-setup/mcp/<server>/`, 否則 `~/.local/share/codex-setup/mcp/<server>/`
- `--runtime-root` 可覆蓋新環境的父目錄, 健康的既有環境優先沿用, 不自動搬移舊 cache runtime
- 已指定的新 server read roots 與選用 `--cert /absolute/cert.pem` 存入 `$CODEX_HOME/mcp-bootstrap.json`, 供重跑沿用, 不保存 Key, Token 或密碼
- Windows Store 程序可能看到套件虛擬路徑, 安裝前檢查 preview 的實際 interpreter 可讀性, 不將這台機器的 sandbox 路徑當成跨機預設

這些 durable data 路徑是此 repo 的部署選擇, 不是 OpenAI 強制規定, 不把新程式或 wheel 放進 Cache

Preview 顯示目的位置, package 版本與 SHA-256, existing/new/pending 狀態, 不建立 runtime, 不寫 config 或設定, 不安裝相依

Apply 核對 wheel CRC / metadata / hash, 建立個別 venv 或沿用現有環境, 安裝固定版本套件, 執行 `pip check` 與離線 stdio fixture 驗證, 然後備份與寫入變動設定, 新 Jev 登錄使用 `-I -B -m codex_jev_mcp.mcp_server`

重複執行相同 bundle 時不重裝 wheel, 不改寫相同設定, 仍執行套件與離線 protocol 檢查, unknown Skill 檔案保留並拒絕覆蓋, managed Skill 變動先備份到 Skill 目錄外並核對內容, config 使用寫入前比對與 readback

套件步驟失敗會保留該 server 註冊, 不阻擋其他獨立項目, runtime 可能已部分安裝, 回報失敗後需檢查該環境, 不把失敗當作已成功, 含未設定 roots 的成功結果仍清楚列 pending 項目

其他維護者正在處理 Skill 鏡像時, 可加入 `--no-skill-sync`, 仍安裝與驗證 runtime, 只略過 managed Skill 同步

Apply 顯示是否需要重新載入 Codex, 檔案與 wheel 已安裝不代表已開啟對話的 MCP process 自動更換, baseline 本身不執行 Jev 語意比較, 不啟用永久紀錄

## Bundle 維護

維護者先取得 preset 指定的五個 wheel, 再整理成同一個本機 bundle, 一般使用者不用逐一填 core/server wheel 或 runtime 路徑

```text
python mcp/scripts/prepare_mcp_bundle.py --wheel-dir /absolute/all-built-wheels
```

預設產物 `dist/mcp/bootstrap/` 包含 wheel, `bundle.json` 與可攜 `installer/`, 使用者在 `installer/` 執行 wrapper 即可, 不必 clone repo, checkout 入口預設也查同一 bundle 位置, `--bundle` 可覆蓋

產生器的 `bundle.json` 標示 `local_unpublished_bundle`, 不自動執行遠端發佈, v0.4.7 release 另提供已核對來源的 baseline portable bundle, Jev wheel 與 SHA-256 manifest. Bundle 包含 5 個第一方 wheel 與 installer, 不包含私人設定或 credential, 公開相依套件仍需對應平台的 wheel cache 或網路. 缺少 bundle / matching wheel 時顯示具體 pending 說明

Jev wheel 建置:

```text
python -m pip wheel --no-deps --wheel-dir /absolute/wheels skills/jev-evaluation
```

CLI 與 MCP 使用同一份 `skills/jev-evaluation/scripts/jev.py`, wheel 以 `codex_jev_mcp` namespace 封裝, public entry points 是 `jev`, `jev-mcp`, `jev-verify`, 單獨 CLI script 與既有 Skill installer 繼續可用

## 獨立監看 repo

`local-activity-monitor` 維護本機網頁與 Jev / Codex collectors, 不維護 API client 或 Skill, Jev metadata writer 位於本 repo 的 `skills/jev-evaluation/`, 文件核心位於 `python-tools/`

監看工具安裝後, 使用 `local-activity-monitor --enable-jev --configure-only` 明確啟用本機紀錄, 以 `--codex --open` 啟動頁面, 預設 `http://127.0.0.1:8787/`, 關閉終端機或 Ctrl+C 停止, `--disable-jev --configure-only` 停用紀錄並保留歷史

只保存 timestamps, operation/source, model, known tokens, latency, body bytes 與安全狀態, 不保存 prompt, query, rubric, candidates, answers, Key 或 raw error, 寫入失敗不影響 Jev, 舊 process 需 reload, 畫面是本機觀察統計, 不代表帳戶總用量或剩餘額度

Codex 只讀近期本機 JSONL metadata, 增量追蹤, 使用 thread 最新累計快照, 不將重複快照加總, 不解析 exec 內容或讀取對話文字 / auth.json, Mac M5 / Linux 的原生執行尚未驗證

## 官方依據

- [Codex MCP 設定](https://learn.chatgpt.com/docs/extend/mcp?surface=cli), [OpenAI Docs MCP](https://developers.openai.com/learn/docs-mcp): stdio / HTTP 與官方唯讀 docs endpoint
- [Context7 client 設定](https://github.com/upstash/context7/blob/master/docs/resources/all-clients.mdx): hosted endpoint 與 client-specific 設定, 只在選用時使用
- [PyPA virtual environments](https://packaging.python.org/en/latest/guides/installing-using-pip-and-virtual-environments/), [XDG data directory](https://specifications.freedesktop.org/basedir/latest/): 隔離環境與 Linux durable data 的依據

## 解除安裝 MCP

一次選擇一個工具, 預覽後才移除, 未指定工具時顯示本機可辨識的獨立 MCP 清單

Windows 使用 `launch-cli.cmd uninstall`, macOS / Linux 使用 `sh launch-cli.sh uninstall`, wheel 提供 `codex-mcp-uninstall`

```text
launch-cli.cmd uninstall context7
launch-cli.cmd uninstall context7 --apply

sh launch-cli.sh uninstall context7
sh launch-cli.sh uninstall context7 --apply

codex-mcp-uninstall --list
codex-mcp-uninstall --tool context7 --apply
```

第一個指令只預覽, `--apply` 在互動終端確認後移除選定註冊, `--apply --yes` 用於已授權的非互動執行, 單獨 `--yes` 仍只預覽

預設保留套件, runtime, credentials, OAuth 授權, 詞表, 規則, notebook 與使用者資料, 設定會先備份, 再檢查 SHA-256 與讀回結果, 其他 MCP 和內建 plugin 不會一起移除

若也要移除 server 套件, 加上 `--remove-package`, 只處理選定 npm prefix 或有 setup 標記的 Python 環境, 其他 MCP 共用的套件會保留, 套件相依與原生 App 也保留

```text
launch-cli.cmd uninstall playwright --remove-package --apply
sh launch-cli.sh uninstall playwright --remove-package --apply
codex-mcp-uninstall --tool playwright --remove-package --apply
```

例如繁中與日文校對都使用 textlint 時, 可以個別移除 MCP 註冊, 不能直接移除共用的 textlint 套件

自訂安裝位置可指定 `--config` 與 `--npm-prefix` 的絕對路徑, 同一工具有多筆註冊時用 `--server` 選定名稱, Windows 可用 `--python` 指定既有 Python 3.11+, macOS / Linux 使用 `CODEX_SETUP_PYTHON`

App / connector 管理的服務要從原本帳戶連接位置解除, 這個入口不取消訂閱或撤銷雲端帳戶授權, 套件移除失敗時會回報註冊已移除與設定備份, 修正套件管理問題後再處理套件

移除後重新開啟使用它的 Codex session, 已執行的 MCP server 不會因設定檔改變而自動停止, 不強制關閉其他工作使用的程序
