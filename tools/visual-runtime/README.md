# 視覺開發本機工具

提供專案框架檢查, 產物 hash 與受控靜態預覽, CLI 與 stdio MCP 共用同一個 Rust 核心
不執行 package scripts, Angular / Nuxt 等開發伺服器沿用專案原本流程

## 建置與安裝

使用 Rust 1.89 以上版本, Setup 以 `cargo install --locked --path <Toolkit>/tools/visual-runtime` 安裝, 也可在 Toolkit 根目錄手動執行同一指令, 執行時不需要 Python
Windows, macOS 與 Linux 使用相同的指令與工具 API, 在目的電腦各自建置, 不複製其他平台的執行檔

## 使用

root 使用實際授權的專案根目錄

```sh
visual-runtime --root /absolute/project inspect
visual-runtime --root /absolute/project artifacts --files index.html app.js
visual-runtime --root /absolute/project preview --entry index.html --files index.html app.js
```

預覽直接綁定 127.0.0.1, 啟動不執行主機名稱查詢
preview 輸出 ready, job ID 與 loopback URL, 前景持續執行直到 Ctrl+C 或程序結束
只提供清單內的檔案快照, 更新檔案後重啟預覽, 不提供 HMR, 目錄瀏覽或整個專案下載
每次至多 128 個資產, 單檔 32 MiB, 合計 64 MiB, 同一程序至多 8 個預覽
拒絕路徑越界, symlink / junction 與隱藏檔, 使用隨機 URL 路徑及嚴格 Host 檢查
預覽中的 HTML / JavaScript 仍可執行其網路行為, 檔案清單只應包含獲准公開給瀏覽器的資產

## MCP

MCP 啟動時不綁定專案, 每次檢查, 資產 hash 或預覽啟動呼叫都必須提供非空白 root
建議使用專案的絕對路徑, 相對資產路徑與越界檢查以該次 root 為準

```toml
[mcp_servers.visual_runtime]
command = "/absolute/.cargo/bin/visual-runtime"
args = ["mcp"]
```

Windows command 改成實際 `visual-runtime.exe` 路徑

| 工具 | 輸入與輸出 |
| --- | --- |
| visual_inspect(root) | root 專案根目錄, 回傳 package.json 的已知框架與版本宣告, scripts 名稱, 不執行 scripts |
| visual_artifacts(root, paths) | paths 相對於該次 root 的檔案清單, 回傳 bytes 與 SHA-256 |
| visual_preview_start(root, entry, files) | entry HTML 與 files 資產清單相對於該次 root, 回傳 job_id, url, ready |
| visual_preview_status | job_id, 只查本程序擁有的工作 |
| visual_preview_stop | job_id, 只關閉本程序擁有的 listener |

同一程序可交錯處理不同 root, 已啟動預覽保留當次資產快照, 後續呼叫不會改變既有預覽內容
8 個預覽上限由同一程序共用, 不依 root 分別增加額度
程序結束時清理自有預覽, 未知 job 不轉成任意 PID 操作
畫面, 互動, console, network 與擷取使用既有瀏覽器工具, 此工具不重造瀏覽器控制層
Three.js, Angular, Vue, React, Unity 與影片選用依專案需求, 不自動安裝引擎或改框架

## 從 Python 版遷移

0.3.0 起改為 Rust 執行檔, MCP 由 `visual-runtime mcp` 啟動, 取代原本的 `visual-runtime-mcp`, 工具名稱, 參數與回傳欄位不變
既有設定把 command 改成新執行檔並加上 `args = ["mcp"]`, 不再需要 Python venv

## 驗證

```sh
cargo test --locked --manifest-path tools/visual-runtime/Cargo.toml
cargo clippy --locked --manifest-path tools/visual-runtime/Cargo.toml --all-targets -- -D warnings
```

測試包含實際 loopback HTTP, 越界, Host, 快照, 工作上限與停止行為, 不代表應用程式本身通過畫面或效能驗收
