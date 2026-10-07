# 測試方式

專案測試使用 Python 標準函式庫 `unittest`, Office 測試資料會使用 `setup/requirements.txt` 中的文件擷取套件

```powershell
python -m unittest discover -s tests -t . -v
```

目前自動測試涵蓋

- CLI 自動發現的全部可執行 module 之 `--help` 可安全執行, `local_documents` 的 MCP 層與驗證由本 repo 的 `mcp/` 管理, 不納入本工具包
- CLI 工具清單、穩定別名與實際 subprocess 輸出
- `launch-cli.cmd` / `launch-cli.ps1` 在任意工作目錄的參數轉送與 exit code
- PowerShell 5.1 / 7 的 PS1 入口, 包含繁中、空白、引號與尾端反斜線參數
- `.env` 無效行, 重複 key, 變數展開, process environment 覆寫與備援處理
- Angular/Nx 元件盤點, 表單欄位規格, generator 衝突與 Git 變更影響測試資料
- Markdown 結構差異與保護取代的 dry-run
- tokenizer 精確計算失敗時的備援估算
- 驗證證據索引與清理預覽
- 欄位規格矩陣的表頭與分隔列
- 文件轉 Markdown 工具的單一輸入, 多輸入多輸出, 多輸入單輸出與輸出衝突
- XLSX, DOCX, PPTX, CSV, TXT 測試資料與圖表覆寫 hash 檢查

語法與 import 檢查

```powershell
python -m compileall -q src packages tests launch-cli.py
```

PDF 擷取器需用實際 PDF 做 `--dry-run`, 因為文字層與表格重建結果會依來源結構而異

```powershell
python launch-cli.py documents.convert_to_markdown C:\path\spec.pdf --dry-run --extracted-at 2026-09-22T14:30:15
```

測試通過只代表這些明確案例, 不表示未提供的文件版面, OCR, Angular 動態中繼資料或遠端 Git 操作已驗證

## Windows 程序稽核 / 清理

```powershell
python -m unittest tests.test_windows_process_audit -v
```

預設只執行模擬資料測試, 涵蓋預設稽核、所有參數遮蔽、PID 重用、ownership / session 變化、父子關係變動、Codex / MCP / 服務保護、快照期限、覆寫保護、缺漏保留、未加 `--apply` 不開啟終止 handle, 以及兩次核對後才終止的呼叫順序

只有明確開啟下列測試才建立並終止真實隔離程序, 不操作電腦上既有的程序, 不需要系統管理員權限

```powershell
$env:MY_PY_TOOLS_PROCESS_LIVE_TEST = '1'
try {
    python -m unittest tests.test_windows_process_audit.IsolatedWindowsProcessTests -v
} finally {
    Remove-Item Env:MY_PY_TOOLS_PROCESS_LIVE_TEST
}
```

真實測試建立短暫 bootstrap 及自己專用的 sleep worker, bootstrap 正常退出後稽核 worker, 驗證無 ownership 不成為候選、預覽仍存活、明確選取及套用後退出, 最後只用已持有的自建 worker handle 清理, 不做整棵程序樹終止, 不驗證第三方服務的所有命令形式或跨平台封裝

Markdown validator focused checks:

```powershell
python -m unittest discover -s tests -t . -p test_validate_structure.py -v
python launch-cli.py markdown.validate_structure --help
```

涵蓋標題跳號, fence closing, hard break, 版本 INFO, exit codes, `-I -S` standalone 執行及 snapshot 產生一致性, 不代表所有 Markdown syntax 已驗證

## 工具清單與免安裝 CLI

```powershell
python -m unittest tests.test_tool_catalog tests.test_distribution tests.test_entrypoints_packaging tests.test_release_tools -v
```

工具清單測試涵蓋可執行模組自動發現、巢狀資料夾、無效語法警告、既有工具別名與獨立 CLI 資源位置

發布測試使用合成 ZIP、模擬 wheel 與 subprocess, 檢查版本、hash、終端機入口、macOS 執行權限、舊 GUI 快取排除、離線資源準備與原生驗證的失敗處理, 不執行本機原生封裝或套件建置

Release CI 的 `distribution.smoke_cli` 會啟動真正的原生成品, 移除 Python 環境變數並縮減 PATH, 驗證離線 token 計算與 TXT 轉換, 不啟動瀏覽器或背景服務

```powershell
python launch-cli.py distribution.smoke_cli C:\path\MyPyToolsCLI\launch-cli.exe
```

這項原生驗證只在已有正式建置產物時執行, 本機模擬測試不代表 macOS 或免安裝執行已驗證
