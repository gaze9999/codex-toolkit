# Local Documents MCP

本目錄維護 MCP server, service, OCR 相依, guarded installer 與 stdio verifier, 文件擷取使用已安裝的 `my-py-document-core` API 2, Markdown 檢視, 保護更新與抽出版定位呼叫原生 `markdown-checks` CLI, 不讀取另一個 repo 的原始碼位置

安裝器預設從 PATH 解析 `markdown-checks`, 也可用 `--markdown-checks` 指定, 並把絕對路徑寫入 MCP 的 `LOCAL_DOCUMENTS_MARKDOWN_CHECKS` 環境變數

本 repo 是原始碼來源, server 不需要部署在此資料夾, `codex-local-documents-mcp` wheel 安裝到使用者的 Python 環境後, 可透過模組或 console command 啟動

- [安裝與獨立部署](../../../docs/setup/cli.md)
- [日常操作教學](../../../docs/usage/local-documents.md)

原 `my-py-tools/mcp_tools/` 已退休, 更新 runtime 使用新 wheel, 搬移或重建 runtime 後重新註冊, 不搬移既有 virtual environment
