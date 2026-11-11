# 第三方來源與授權

| 元件 | 上游 | 授權 | 保留方式 |
| --- | --- | --- | --- |
| Edge DevTools MCP | [chrome-devtools-mcp](https://github.com/ChromeDevTools/chrome-devtools-mcp), 版本與 SHA-256 見 [upstream.json](../mcp/mcp_servers/edge_devtools/upstream.json) | Apache-2.0 | 建置 wheel 時從官方 `.tgz` 帶入上游 `THIRD_PARTY_NOTICES` |

Python 相依套件依各自 `pyproject.toml` 或 `requirements.txt` 由安裝環境取得, 授權隨套件 metadata 保留
