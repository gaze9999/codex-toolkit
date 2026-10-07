# Local Documents MCP

本目錄維護 MCP server, service, OCR 相依, guarded installer 與 stdio verifier, 公開文件與 Markdown 功能使用已安裝的 `my-py-document-core` API 1, 不讀取另一個 repo 的原始碼位置

本 repo 是原始碼來源, server 不需要部署在此資料夾, `codex-local-documents-mcp` wheel 安裝到使用者的 Python 環境後, 可透過模組或 console command 啟動

- [安裝與獨立部署](../../../docs/setup/cli.md)
- [日常操作教學](../../../docs/usage/local-documents.md)

原 `my-py-tools/mcp_tools/` 已退休, 更新 runtime 使用新 wheel, 搬移或重建 runtime 後重新註冊, 不搬移既有 virtual environment
