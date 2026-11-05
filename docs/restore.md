# 依個人設定還原環境

## 選定專案指引與暫存

`mcp/scripts/manage_agent_files.py` 提供 `snapshot`、`restore`、`claude`、`ignore`, 預設只預覽, `--apply` 才寫入
這些命令不改帳戶、remote、tracked 來源、用戶端設定或權限, 不代替專案驗收

```text
python mcp/scripts/manage_agent_files.py snapshot --repo <source-checkout> --file AGENTS.md --file .codex/agents/reviewer.toml --bundle <new-private-directory>
python mcp/scripts/manage_agent_files.py restore --repo <same-repository-checkout> --bundle <snapshot>
python mcp/scripts/manage_agent_files.py claude --repo <project> --entry AGENTS.override.md --roles-root <private-owner> --role .codex/agents/reviewer.toml
python mcp/scripts/manage_agent_files.py ignore --repo <project> --profile <private-ignore-profile> --group browser
```

`snapshot` 只讀明確選取的工作規範、參考與角色, 附 repo 身分、revision 及逐檔 hash, 不收 auth/config/settings
`restore` 比對相同 repo 身分與快照 hash, 不同本機內容保留為 CONFLICT, 審閱後 `--apply --replace` 才備份並取代
已追蹤內容由 Git owner 維護, junction / symlink 請回到正式來源, 不複製裝置連結
必要的相對參考也要列入 `--file`, 其他 repo 的引用先取得對應私人來源, 不以一份檔案快照宣稱整個專案已可執行

`claude` 產生匯入有效 AGENTS 入口的 `CLAUDE.md`, 只轉接三欄 `name`、`description`、`developer_instructions` 的 Codex 角色
含工具、模型、權限或沙箱欄位就停止, 由 owner 設計原生定義, 不靜默丟棄限制, 有效用戶端載入另行核對
`--roles-root` 指向已確認的私人角色 owner, 不從已安裝連結讀取, 不改寫既有 tracked `CLAUDE.md`
已有正式 `CLAUDE.md` 時, 加上 `--claude-entry CLAUDE.local.md` 產生本機匯入入口, 保留原檔

ignore profile 格式為 `{"schema_version":1,"groups":{"browser":["/.playwright-mcp/"]}}`, 可重複 `--group`
工具合併到 Git 回報的 `info/exclude`, 備份既有內容, 拒絕命中 tracked 檔案, 不刪檔、不取消追蹤、不改全機忽略設定
替換指引的備份保存在該 repo 的 Git common directory 下 `agent-file-backups/`, 產物的精確本機排除與既有規則保留
完成後重跑預覽核對 CURRENT, 失敗回傳 JSON `blocked` 與結束碼 2, 不把部分成功當整套完成

依據: [Git ignore](https://git-scm.com/docs/gitignore)、[Claude 指示](https://code.claude.com/docs/en/memory)、[Claude 角色](https://code.claude.com/docs/en/sub-agents), 核對日期 2026-11-04

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
