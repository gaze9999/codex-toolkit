# 安裝包與建置

## 產品與來源

| 產品 | 來源 / builder | 必要條件 |
|---|---|---|
| Skills | `skills/`, `prepare_release.py` | Python 3.10+, 完整來源 |
| Plugins | `plugins/catalog.json`, `prepare_plugin_release.py` | Python 3.11+, 完整 Git checkout |
| 應用程式來源 | `tooling/products.json`, `tooling/package.py` | Python 3.11+, 明確產品選取 |
| MCP wheels / installer | `prepare_mcp_release.py` | 各 package 的 build backend, 固定上游來源及網路 |
| 原生 CLI | `prepare_cli_release.py` | 原生 Windows / macOS runner, requirements 固定的 standalone Python |

產品選項、manifest 欄位與預覽 / 建置 / 讀回操作見 [打包工具](../operating-model.md), Plugin 檢查及市集生成見 [Plugins](../plugins.md)

## 相依設定

在隔離 Python 環境安裝 [發布相依](../../mcp/tools/release.requirements.txt), 此清單引用 [Jev requirements](../../skills/jev-evaluation/requirements.txt) 中的固定 MCP SDK. Skill audit 使用啟動它的 Python 執行 helper, 該 interpreter 必須具備這些相依

```text
python -m pip install -r mcp/tools/release.requirements.txt
python -B mcp/scripts/audit_skills.py
```

已有相容環境具備 Jev MCP SDK 時, 可使用 `--python-executable` 指定 helper 的 Python, 沿用既有相依套件:

```text
python -B mcp/scripts/audit_skills.py --python-executable /path/to/python-with-jev-sdk
```

MCP 各 package 的版本由自己的 `pyproject.toml` 保存, 第三方版本、來源及授權 hash 由 `mcp/tools/mcp-wheels.requirements.json` 管理. 獨立 Python 工具的建置見 [Python 使用說明](../../python-tools/docs/standalone.md)

## Skills ZIP

```text
python -B mcp/scripts/prepare_release.py --dry-run
python -B mcp/scripts/prepare_release.py --version 0.2.0
```

產物在 `dist/<tag>/`, `all-skills-<tag>.zip` 頂層直接放各 Skill 目錄, `release-manifest.json` 保存 Skill 版本、檔案集合與 ZIP hash. 工具動態尋找含 `SKILL.md` 的來源, 保留個別版本、UI metadata、policy 與 dependencies, 同版本只更新工具管理且未被另行修改的輸出

## MCP 與 CLI

```text
python -B mcp/scripts/prepare_mcp_release.py --help
python -B mcp/scripts/prepare_cli_release.py --help
python -B tooling/package.py plan --product mcp --product portable-cli
```

MCP builder 在隔離副本建置第一方 core / adapters、固定第三方 wheel 與 installer, 產物包含版本、來源 hash 與第三方授權. CLI builder 使用 `mcp/tools/cli-release.requirements.json` 的 Python 及套件, 在選定平台建置並執行搬移後的啟動 / 結束檢查. `--verify` 讀回既有 CLI archive

穩定 1.0.0 起, `.github/workflows/cli-release.yml` 處理原生 CLI, `python-tools-release.yml` 處理 Python core wheel, `plugin-release.yml` 處理 Plugin ZIP, 版本門檻見 [CLI workflow 的實際門檻](../../.github/workflows/cli-release.yml). 手動 workflow 的輸出與 Release 資產依各自事件條件設定

## 版本與發布設定

Skill、Plugin、Python package 及 Toolkit 整包各自使用版本. 相容修正增加 patch, 相容功能增加 minor, 不相容介面增加 major, 整包版本由 `VERSION` 保存. Skill 顯示名稱使用 `Name (vX.Y.Z)`, 呼叫名稱保持 `$skill-name`

發布來源須乾淨、已提交且受 Git 追蹤, 每個輸出附 SHA-256 與來源 manifest. 安裝與啟用透過原生用戶端入口, 更新後重新載入並確認工具與 Skill discovery

GitHub Release 需明確授權, 使用新版本 Tag 並指向已核對的提交, 保存 README、LICENSE、必要第三方 notices 與相應資產. Release 說明列使用者可見變更、相容性及必要升級操作
