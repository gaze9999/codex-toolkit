# 版本與發布

repository 版本記錄於根目錄 `VERSION`, 使用 SemVer, Git Tag 加上 `v` 前綴, 例如 `VERSION=0.2.0` 對應 `v0.2.0`

`my-py-document-core` 與 `my-py-workspace-core` 是用途不同的 Python 套件, 各自以 `pyproject.toml` 管理套件版本, repository Tag 不強迫兩個 wheel 使用同一版本, release manifest 會記錄實際組合

## 準備發布

正式發布先更新 `VERSION`, 檢查 diff, 本機只需執行與修改相關的單元測試、設定及文件檢查, 不需要建置 EXE、app、ZIP 或 wheel, `prepare --dry-run` 仍會建置暫存 wheel, 不屬於最小測試

提交並推送確認過的來源後, 建立指向該 commit 的新 Tag 與 GitHub Release, `release: published` 會觸發雲端來源與平台建置, CI 的 `source` 工作安裝 `setup/requirements-release.txt`, 執行 `scripts.release prepare`, 產生並驗證來源 ZIP、兩個核心 wheel 與來源資訊清單

來源與 CLI 工作全部通過後才上傳正式附件, 建立 Release 不代表產物已就緒, 請確認 Actions 結果與附件清單, 已發布 Tag 與附件不重寫

### 選用的本機來源封裝

以下 helper 仍可供維護者自行檢查來源包, 會建置套件, 不要在只做最小測試的情境執行

```powershell
python launch-cli.py scripts.release prepare --dry-run
```

確認要準備目前版本或指定下一個 repository 版本

```powershell
python launch-cli.py scripts.release prepare
python launch-cli.py scripts.release prepare --version 0.3.0
python launch-cli.py scripts.release prepare --asset-root C:\path\release-assets
```

`prepare` 會執行 `unittest` 與不產生 bytecode 的 Python AST 語法檢查, 在隔離的暫存副本建置兩個 wheel, 驗證 wheel CRC 與 metadata, 再產生

```text
dist/v0.2.0/
├── my-py-tools-v0.2.0.zip
├── my_py_document_core-<package-version>-py3-none-any.whl
├── my_py_workspace_core-<package-version>-py3-none-any.whl
└── release-manifest.json
```

來源 ZIP 遵循 Git ignore, 排除 `.env`, credentials, private key, cache, log, build 與中間產物, 但保留 `.env.example`, manifest 記錄每個 asset 的大小與 SHA-256

工具原始碼位於 `src/`, 相依與選用設定位於 `setup/`, 測試程式碼保留於來源包, 舊介面的本機快取及 Runtime 不納入來源 ZIP 或核心 wheel

同一版本只能取代由本工具管理且內容未被另行修改的輸出, 發現未知檔案或 hash 不符時會停止, 不覆寫現有資料

## 選用的本機來源發布

先檢查 diff 與 manifest, 自行 commit 預定發布的來源變更, helper 不會自動 commit

```powershell
python launch-cli.py scripts.release publish v0.2.0
python launch-cli.py scripts.release publish v0.2.0 --asset-root C:\path\release-assets
```

`--asset-root` 適合 sandbox 與 GitHub CLI 使用不同檔案權限的環境, 指定資料夾下仍使用 `<tag>/` 結構與同一份 manifest/hash 驗證, 不會放寬來源檢查

`publish` 要求乾淨 working tree, 目前 branch 追蹤同名 `origin` branch, 本機與遠端 Tag 尚不存在, GitHub CLI 已登入, 並重新執行來源驗證, 輸入完整 Tag 確認後才 push branch 與建立 GitHub Release, 最後核對遠端 asset 名稱與大小

`codex-toolkit` 管理 Skills / Plugin、MCP 與獨立 Python 工具的發布流程, 本流程負責 Python 來源包、核心 wheel 與 CLI 免安裝包, 既有套件及產物名稱保留相容性

## Windows 與 macOS 免安裝 CLI

正式產物由 `.github/workflows/release.yml` 的 `Release source and standalone CLI` 建置, 原始碼工作與三個平台工作全部成功後才上傳, 不把本機產物當成正式成品

| 平台 | 成品 |
| --- | --- |
| Windows x64 | `my-py-tools-<version>-cli-windows-x64.zip` |
| macOS Apple Silicon | `my-py-tools-<version>-cli-macos-arm64.zip` |
| macOS Intel | `my-py-tools-<version>-cli-macos-x64.zip` |

每份 CLI ZIP 內含 Python、文件處理套件及離線 tokenizer 編碼, 必須保留整個 `MyPyToolsCLI/` 資料夾與 `_internal/`, 沒有桌面、瀏覽器或 WebView2, Git 類工具仍需要系統 Git

`cli-manifest-<os>-<architecture>.json` 記錄版本、Python、相依套件、工具、來源限定工具、終端機模式、入口、大小及 SHA-256, helper 核對 ZIP CRC、路徑、工具清單位置與 macOS 執行權限, 拒絕混入舊 GUI / Web 入口

CI 在移除 Python 環境變數並縮減 PATH 的環境驗證清單、離線 tokenizer、TXT 轉 Markdown、來源限定工具阻擋與已移除的 `--web` 選項, Windows 另外驗證 CMD / PS1 入口

發布工作只上傳十個附件: 來源 ZIP、兩個核心 wheel、來源資訊清單、三個 CLI ZIP 與三個平台資訊清單, 不覆寫既有附件, 上傳後核對 GitHub 回傳的大小與 SHA-256

### 使用方式

Windows 解壓縮後

```powershell
.\MyPyToolsCLI\launch-cli.cmd --list
.\MyPyToolsCLI\launch-cli.ps1 document-to-markdown "C:\path\spec.docx"
```

macOS 依 CPU 選 arm64 或 x64

```bash
./MyPyToolsCLI/launch-cli --list
./MyPyToolsCLI/launch-cli documents.convert_to_markdown /path/spec.docx
```

Windows PS1 在原始碼目錄呼叫 Python, 在免安裝包呼叫相鄰的 `launch-cli.exe`, 保留目前工作目錄、參數與結束代碼, 執行政策不允許腳本時可改用 CMD, 不自動調整系統執行政策

CLI 輸出使用 UTF-8, 發布工具需要完整儲存庫、開發用 Python 與 GitHub CLI, 免安裝版可查看其 `--help`, 執行時會提示改用原始碼入口

### CI 設定與本機檢查

工作流程由 `release: published` 觸發, 也可手動指定既有 Release Tag, Tag 的 `VERSION` 必須一致, 不會自行變更版本、commit 或重寫 Tag

不再需要 Workbench UI 讀取 token、Node.js 或 WebView2 URL / hash 設定, 舊遠端 Secret / Variable 不會由程式自行刪除

CI 安裝 `setup/requirements-cli-build.txt`, 使用 Python 3.14 在目標平台建置, helper 可供維護者在明確需要時手動使用

```powershell
python launch-cli.py scripts.release cli v0.4.2 --asset-root dist/cli
python launch-cli.py distribution.smoke_cli C:\path\MyPyToolsCLI\launch-cli.exe
```

本機最小檢查只執行相關測試, 不執行上述原生建置, 也不執行會建立 wheel 的 `prepare --dry-run`

```powershell
python -m unittest tests.test_tool_catalog tests.test_distribution tests.test_entrypoints_packaging tests.test_release_tools -v
```

此次 CLI-only 改版的 Windows / macOS 原生成品與附件上傳須由後續 Release CI 驗收, 本機單元測試不代表跨平台封裝成功, 本次變更不修改既有 Release 附件
