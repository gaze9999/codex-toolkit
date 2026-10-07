# Python Tools

目前獨立工具版本 `0.4.2`, 提供可獨立使用的 Python 工具, 涵蓋常用文件轉 Markdown、Markdown 安全更新、Angular/Nx 程式碼盤點、開發產物清理與驗證證據整理

根目錄的操作入口統一使用 `launch-xxx` 命名, 工具原始碼集中在 `src/`, 相依清單與選用設定集中在 `setup/`, README、版本、Python 套件與 Git 設定仍保留在根目錄

Windows 使用 `launch-cli.cmd` 或 `launch-cli.ps1`, macOS 使用 `python launch-cli.py`, 以終端機選取工具及操作參數

## CLI 入口

Release CI 為 Windows x64、macOS arm64 與 macOS x64 分別建置 CLI 免安裝 ZIP, 內含 Python 與文件套件, 不依賴 Node.js、Workbench UI 或瀏覽器 Runtime, 改版後成品須通過 CI 原生驗證才提供下載

CLI 免安裝包需保留整個 `MyPyToolsCLI/` 資料夾, Windows 在終端機執行 `MyPyToolsCLI\launch-cli.exe --list`, macOS 執行 `./MyPyToolsCLI/launch-cli --list`, 工具參數與下方的原始碼入口相同

原始碼版需要 Python 3.10+, Windows 也可使用 Python 3.14

```powershell
.\launch-cli.cmd --list
.\launch-cli.cmd documents.convert_to_markdown "C:\path\spec.docx"
.\launch-cli.cmd document-to-markdown --help
```

Windows 本機 CLI 使用 `launch-cli.cmd`, 優先使用專案的 `.venv` Python, 不存在時使用 PATH 中可執行的 Python, macOS 原始碼版使用 `python launch-cli.py`, 呼叫時可以在任意工作目錄使用啟動檔的完整路徑, 輸入與輸出仍依目前工作目錄及明確參數解析

PDF、Office 文件及精確 token 計算需要選用相依套件, 由開發環境安裝, 不在每次啟動時自動下載

```powershell
python -m pip install -r setup/requirements.txt
```

多個來源可分別輸出或合併成單一 Markdown

```powershell
python launch-cli.py documents.convert_to_markdown spec.pdf api.xlsx --output-dir markdown-output
python launch-cli.py documents.convert_to_markdown spec.pdf api.xlsx --combine-output combined.md
```

## 分類與教學

| 原始碼 | 用途 | 教學 |
| --- | --- | --- |
| `src/angular/` | 元件盤點、表單欄位規格檢查、generator 預檢與 Git 變更影響 | [Angular / Nx](docs/angular-tools.md) |
| `src/documents/` | 文件轉 Markdown、欄位矩陣擷取與抽出版定位 | [文件處理](docs/document-tools.md) |
| `src/markdown/` | 結構檢查、差異與 SHA-256 保護更新 | [Markdown](docs/markdown-tools.md) |
| `src/maintenance/` | Windows 程序稽核、產物隔離清理、環境比對與 Git 歷史身分改寫 | [維護](docs/maintenance-tools.md) |
| `src/text/`, `src/validation/` | token 計數與既有驗證證據索引 | [文字與驗證](docs/text-validation-tools.md) |
| `src/shared/` | 選用變數、版本、工具清單與核心載入 | [設定](docs/configuration.md) |
| `src/scripts/` | 來源 ZIP、核心 wheel 與明確確認的發布流程 | [發布](docs/releases.md) |
| `src/distribution/` | 獨立 CLI 免安裝包的原生建置 | [發布](docs/releases.md) |
| `src/my_py_document_core/`, `packages/workspace_core/` | 用途獨立的可重用 Python 核心 | [文件核心](docs/python-document-core.md), [工作區核心](docs/python-workspace-core.md) |
| `tests/` | 可重現的測試程式碼, 保留於 Git | [測試](docs/testing.md) |
| `setup/` | CLI 與打包相依清單與 `.env.example` | [設定](docs/configuration.md) |

新增工具放在 `src/<用途>/`, 模組名稱仍是 `<用途>.<工具>`, CLI 自動發現具有 `__main__` 入口的工具, 不再從根目錄使用舊的 `python -m <用途>.<工具>` 命令, 新增方式見 [CLI 擴充教學](docs/configuration.md#新增-cli-工具)

## 設定與安全

`setup/.env` 是選用的非路徑變數設定, 缺少或無效時使用安全預設值, 可複製 `setup/.env.example` 後自訂, 輸入、輸出及專案路徑仍以 CLI 參數為準

多數工具唯讀或只寫入指定輸出, Markdown 更新需要 `--write`, 產物清理預設預覽, Git 歷史改寫會建立備份並再次要求確認, 轉換後的 Markdown 供搜尋與定位, 原始文件仍是權威來源

Git 工具需要 Git, 發布工具需要完整原始碼、開發用 Python 與已登入的 GitHub CLI, CLI 免安裝版會提示需原始碼的工具改用完整儲存庫, MCP 與 Skills 由同一儲存庫的整合層管理

## 驗證與發布

```powershell
python -m unittest discover -s tests -t . -v
```

獨立工具版本由 `VERSION` 管理, 文件核心及工作區核心維持獨立套件版本, `prepare --dry-run` 仍會建置暫存 wheel, 最小本機檢查不需執行, 詳細安全檢查與發布操作見 [發布教學](docs/releases.md), 本機產物不會自動 commit、push 或發布

第一方工具採 [MIT](../LICENSE), 相依套件保留原授權
