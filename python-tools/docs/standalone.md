# 脫離 Codex 使用 Python 工具

Python CLI 與核心套件可單獨使用, 不需安裝 Codex、市集、Skill 或啟動 MCP. Plugin 提供工作流程與部分 helper, 完整獨立工具來源在 `python-tools/`

| 用法 | 取得內容 | 相依與說明 |
|---|---|---|
| 執行工具 | 完整 `python-tools/` 目錄 | Python 3.10+, [CLI 教學](../README.md) |
| 嵌入 Python 程式 | 文件 / 工作區 core wheel | [文件核心](python-document-core.md), [工作區核心](python-workspace-core.md) |
| 使用 PDF / Office | CLI 或 core 加選用套件 | `setup/requirements.txt`, [文件教學](document-tools.md) |
| 複製 Plugin 內的 helper | 該 Skill 的 scripts 及其必要檔案 | 先讀 helper 的 CLI help、相依與來源 manifest, 不只取單一檔案 |

取得來源後, 可只保留完整 `python-tools/` 目錄與 MIT LICENSE, 不需保留 Plugin 生成目錄. 執行時使用入口的完整路徑, 輸入、輸出與專案路徑由參數決定

```text
python /path/to/python-tools/launch-cli.py --list
python /path/to/python-tools/launch-cli.py documents.convert_to_markdown --help
python /path/to/python-tools/launch-cli.py documents.convert_to_markdown sample.txt --output-dir output --dry-run
```

簡單文字與唯讀盤點通常可先直接執行, PDF / Office、token 計數等功能依 help 安裝所需套件. 保留 `src/`、`setup/`、`VERSION`、核心套件與相關文件, 不搬另一台電腦的 venv 或 runtime

安裝到自己的虛擬環境:

```text
python -m venv .venv
# Windows: .venv/Scripts/python, macOS/Linux: .venv/bin/python
<venv-python> -m pip install -r /path/to/python-tools/setup/requirements.txt
<venv-python> /path/to/python-tools/launch-cli.py --list
```

只需要核心時在 `python-tools/` 建置 wheel, 工作區核心從 `packages/workspace_core/` 建置. 各自安裝到自己的環境後可移除來源 checkout, 核心 API 不依賴 Codex 設定或 MCP imports. 呼叫範例與必要相依見各核心文件

工具更新時核對版本、hash 與相容性, 寫入或清理先預覽, 案例只使用自己的授權資料. 原始規格保有判定權, Markdown 抽出版用於搜尋與定位
