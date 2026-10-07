# Edge DevTools MCP

提供 Codex 使用的 Edge 網頁除錯工具, 包含 DOM / JavaScript 檢查, console 訊息, network request 與效能 trace. Wheel 內含固定版本 `chrome-devtools-mcp@1.10.1` 的官方 JavaScript runtime, Apache-2.0 授權與第三方 notices, 啟動時不下載 npm 套件

需要 Python 3.11+, 已安裝 Microsoft Edge, 以及符合 `^20.19.0`, `^22.12.0` 或 `>=23` 的 Node.js. 各電腦使用自己的 Edge 執行檔與獨立 Python 環境

```text
python -m pip install codex_edge_devtools_mcp-0.1.0-py3-none-any.whl
edge-devtools-mcp --check
edge-devtools-mcp
```

預設使用 headless Edge 與暫時隔離 profile, 關閉 usage statistics, CrUX 網址查詢與更新檢查. `--headed` 可顯示隔離視窗, `--executable-path` 可指定其他 Edge channel, `--node-path` 可指定 Node 執行檔

從本 setup 安裝並註冊至 Codex:

```text
python mcp/scripts/install_development_tool.py --tool edge-devtools --interface mcp
python mcp/scripts/install_development_tool.py --tool edge-devtools --interface mcp --wheel-dir <absolute-wheel-directory> --apply
```

重新載入 Codex 後使用 `edge_devtools` 的工具. 要除錯既有的登入狀態時, 先自行以獨立 profile 啟用 Edge 的 loopback remote debugging, 再明確設定 `--browser-url http://127.0.0.1:9222`. 此模式會讓 MCP 存取該 session 的頁面與登入資料

建置 wheel 時依 `upstream.json` 的官方來源與 SHA-256 下載 runtime, 可用 `CODEX_EDGE_MCP_ARCHIVE` 指定已下載的相同 `.tgz` 供離線建置, checksum 必須相符

[Microsoft Edge 官方設定](https://learn.microsoft.com/en-us/microsoft-edge/web-platform/devtools-mcp-server), [官方 MCP 原始碼](https://github.com/ChromeDevTools/chrome-devtools-mcp)
