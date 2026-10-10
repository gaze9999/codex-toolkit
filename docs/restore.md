# 依個人設定還原環境

使用公開 Toolkit 的同一份安裝器, 將個人選用項目保存在自己的私人 repository. Profile 只包含來源版本、Skill / Plugin 名稱、平台工具選項與手動步驟, credentials 留在各台電腦

## 準備來源與預覽

需要 Git、Python 3.11+ 及支援 Plugin 的 Codex CLI. 取得 Toolkit 後 checkout 個人 profile 指定的完整 commit SHA, 保持工作樹乾淨

```text
git clone https://github.com/gaze9999/codex-toolkit.git
git -C codex-toolkit checkout <profile-toolkit_revision>
python codex-toolkit/mcp/scripts/restore_profile.py --profile /path/to/private/profiles/workstation.json
```

Profile 格式:

```json
{
  "schema_version": 1,
  "toolkit_revision": "<reviewed-40-character-commit-sha>",
  "agents_source": "../agents",
  "skills": ["readme-maintainer"],
  "plugins": ["codex-agent-workflow"],
  "tools": {
    "windows": [{"id": "context7", "interface": "mcp"}],
    "macos": [{"id": "context7", "interface": "mcp"}]
  },
  "manual": ["在目標電腦登入帳戶, 另設允許的資料目錄"]
}
```

`agents_source` 相對於 profile 所在目錄, 提供自己的 `AGENTS.md` 與 `subagents.config.toml`, 可附 `references/` 內的 Markdown, 還原時保留相對路徑. 參考文件按適用條件讀取. 範例 SHA 是待填值, 不可直接套用. 詳細元件版本由已核對的 Toolkit revision 決定

## 套用指定範圍

```text
python codex-toolkit/mcp/scripts/restore_profile.py --profile /path/to/private/profiles/workstation.json --apply
python codex-toolkit/mcp/scripts/restore_profile.py --profile /path/to/private/profiles/workstation.json --section tools
python codex-toolkit/mcp/scripts/restore_profile.py --profile /path/to/private/profiles/workstation.json --section tools --apply
```

預設範圍是 agents、skills、plugins, 工具需明選 `--section tools`. 可重複 `--section` 限定處理範圍, `--codex-home` 可指定獨立安裝位置. Profile 是使用者審查的套用範圍, 安裝器逐項處理其選用項目

Global、subagent 設定或參考文件內容不同時, agents 安裝器停止整批寫入, 明確取代使用 `--apply --replace-agents`, 安裝器先按相對路徑保存備份. 來源參考文件及目標路徑拒絕 symbolic link / junction, 目標其他檔案保留. Skill 使用既有 preview、備份與內容衝突檢查, Plugin 使用原生管理入口. 既有市集來源、其他 Plugin owner 或直接 Skill 重複時先處理衝突, 不自動開啟另一份來源

各步驟依序執行, 失敗會停止並指出已完成範圍, 不宣稱整組交易回復. 重跑前先核對已完成步驟與安裝器備份

Desktop Git / 偏好可另產生片段, 合併同名 table 與欄位, 保留其他設定:

```text
python codex-toolkit/mcp/scripts/render_desktop_settings.py --source-root /path/to/private/agents --output desktop-fragment.toml
```

套用完成後重新載入 Codex, 分開確認 Skill、工具探索、帳戶授權與代表性呼叫. 裝置路徑、帳戶與允許的 roots 在各台電腦設定, macOS 原生結果需在 Mac 驗證
