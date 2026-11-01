# 視覺開發本機工具

提供專案框架檢查、產物 hash 與受控靜態預覽, CLI / MCP 共用 Python 核心
需要 Python 3.11+, 核心無第三方相依, 選配 MCP 使用 mcp 2.2.0
不執行 package scripts, Angular / Nuxt 等開發伺服器沿用專案原本流程

## 使用

在套件目錄安裝, root 使用實際授權的專案根目錄

```sh
python -m pip install ".[mcp]"
visual-runtime --root /absolute/project inspect
visual-runtime --root /absolute/project artifacts --files index.html app.js
visual-runtime --root /absolute/project preview --entry index.html --files index.html app.js
```

preview 輸出 ready、job ID 與 loopback URL, 前景持續執行直到 Ctrl+C
只提供清單內的檔案快照, 更新檔案後重啟預覽, 不提供 HMR、目錄瀏覽或整個專案下載
每次至多 128 個資產、單檔 32 MiB、合計 64 MiB, 同一程序至多 8 個預覽
拒絕路徑越界、symlink / junction 與隱藏檔, 使用隨機 URL 路徑及嚴格 Host 檢查
預覽中的 HTML / JavaScript 仍可執行其網路行為, 檔案清單只應包含獲准公開給瀏覽器的資產

MCP 設定範例, Windows command 改成實際 Scripts/visual-runtime-mcp.exe

```toml
[mcp_servers.visual_runtime]
command = "/absolute/venv/bin/visual-runtime-mcp"
args = ["--root", "/absolute/project"]
```

| 工具 | 輸入與輸出 |
| --- | --- |
| visual_inspect | 無參數, 回傳 package.json 的已知框架與版本宣告、scripts 名稱, 不執行 scripts |
| visual_artifacts | paths 相對檔案清單, 回傳 bytes 與 SHA-256 |
| visual_preview_start | entry HTML 與 files 資產清單, 回傳 job_id、url、ready |
| visual_preview_status | job_id, 只查本程序擁有的工作 |
| visual_preview_stop | job_id, 只關閉本程序擁有的 listener |

程序結束時清理自有預覽, 未知 job 不轉成任意 PID 操作
畫面、互動、console、network 與擷取使用既有瀏覽器工具, 此工具不重造瀏覽器控制層
Three.js、Angular、Vue、React、Unity 與影片選用依專案需求, 不自動安裝引擎或改框架

```sh
python -m unittest discover -s tests -v
```

測試包含實際 loopback HTTP、越界、Host、快照與停止行為, 不代表應用程式本身通過畫面或效能驗收
