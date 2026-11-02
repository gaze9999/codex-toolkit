# 視覺開發本機工具

提供專案框架檢查、產物 hash 與受控靜態預覽, CLI / MCP 共用 Python 核心
需要 Python 3.11+, 核心無第三方相依, 選配 MCP 使用 mcp 2.2.0
不執行 package scripts, Angular / Nuxt 等開發伺服器沿用專案原本流程

## 平台與安裝入口

Windows、macOS 與 Linux 使用相同的 Python 套件與工具 API, 在目的電腦以 Python 3.11+ 建立自己的 venv

| 平台 | MCP 可執行檔 | 每次呼叫的 root 範例 |
| --- | --- | --- |
| Windows | venv/Scripts/visual-runtime-mcp.exe | C:/path/to/project |
| macOS / Linux | venv/bin/visual-runtime-mcp | /path/to/project |

macOS 安裝時, 將下列來源與 venv 路徑替換為目的電腦的實際路徑, venv 使用尚未占用的資料夾

```sh
python3 -m venv /path/to/visual-runtime-venv
/path/to/visual-runtime-venv/bin/python -m pip install "/path/to/codex-toolkit/python-tools/packages/visual-runtime[mcp]"
/path/to/visual-runtime-venv/bin/visual-runtime-mcp --help
```

MCP 設定使用該平台可執行檔的絕對路徑, 啟動時不帶 --root, 專案 root 隨工具呼叫傳入
搬移時在 Mac 重建 venv 與相依套件, 不複製 Windows 的 venv 或 .exe

## 使用

在套件目錄安裝, root 使用實際授權的專案根目錄

```sh
python -m pip install ".[mcp]"
visual-runtime --root /absolute/project inspect
visual-runtime --root /absolute/project artifacts --files index.html app.js
visual-runtime --root /absolute/project preview --entry index.html --files index.html app.js
```

預覽直接綁定 127.0.0.1, 啟動不執行主機名稱查詢
preview 輸出 ready、job ID 與 loopback URL, 前景持續執行直到 Ctrl+C
只提供清單內的檔案快照, 更新檔案後重啟預覽, 不提供 HMR、目錄瀏覽或整個專案下載
每次至多 128 個資產、單檔 32 MiB、合計 64 MiB, 同一程序至多 8 個預覽
拒絕路徑越界、symlink / junction 與隱藏檔, 使用隨機 URL 路徑及嚴格 Host 檢查
預覽中的 HTML / JavaScript 仍可執行其網路行為, 檔案清單只應包含獲准公開給瀏覽器的資產

MCP 啟動時不綁定專案, 每次檢查、資產 hash 或預覽啟動呼叫都必須提供非空白 root
建議使用專案的絕對路徑, 相對資產路徑與越界檢查以該次 root 為準
Windows command 改成實際 Scripts/visual-runtime-mcp.exe

```toml
[mcp_servers.visual_runtime]
command = "/absolute/venv/bin/visual-runtime-mcp"
```

| 工具 | 輸入與輸出 |
| --- | --- |
| visual_inspect(root) | root 專案根目錄, 回傳 package.json 的已知框架與版本宣告、scripts 名稱, 不執行 scripts |
| visual_artifacts(root, paths) | paths 相對於該次 root 的檔案清單, 回傳 bytes 與 SHA-256 |
| visual_preview_start(root, entry, files) | entry HTML 與 files 資產清單相對於該次 root, 回傳 job_id、url、ready |
| visual_preview_status | job_id, 只查本程序擁有的工作 |
| visual_preview_stop | job_id, 只關閉本程序擁有的 listener |

同一程序可交錯處理不同 root, 已啟動預覽保留當次資產快照, 後續呼叫不會改變既有預覽內容
8 個預覽上限由同一程序共用, 不依 root 分別增加額度
程序結束時清理自有預覽, 未知 job 不轉成任意 PID 操作
畫面、互動、console、network 與擷取使用既有瀏覽器工具, 此工具不重造瀏覽器控制層
Three.js、Angular、Vue、React、Unity 與影片選用依專案需求, 不自動安裝引擎或改框架

## 從 0.1.x 遷移

0.2.0 的 MCP 不再接受啟動參數 --root, 從 MCP args 移除該參數及路徑
原 visual_inspect、visual_artifacts、visual_preview_start 呼叫新增 root, 例如預覽啟動:

```json
{"root":"/absolute/project","entry":"index.html","files":["index.html","app.js"]}
```

visual_preview_status 與 visual_preview_stop 沿用 job_id, CLI 的 --root 操作方式維持相同

## 驗證

```sh
python -m unittest discover -s tests -v
```

測試包含實際 loopback HTTP、越界、Host、快照與停止行為, 不代表應用程式本身通過畫面或效能驗收
