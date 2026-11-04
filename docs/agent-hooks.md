# Claude / Codex 共用 Hooks

版本 0.1.0, 需要 Python 3.11 以上與 Git
共用核心為 `mcp/scripts/agent_hooks.py`, 安裝入口為 `mcp/scripts/install_agent_hooks.py`
個人選項放在工具來源以外的 JSON profile, 執行時不依賴原 checkout

| 事件 | 行為 | 輸出 |
| --- | --- | --- |
| SessionStart | 找出 Git 根目錄、分支與 profile 指定且實際存在的入口, 壓縮後重新提供索引 | 最多 1,600 個字元, 同工作階段相同索引略過 |
| PostToolUse | Edit / Write / MultiEdit / apply_patch 後, 對有變化的已追蹤 diff 執行 `git diff --check` | 成功安靜, 失敗提示執行原命令取得位置 |
| Stop | 核對目前 diff 是否有本工作階段的空白檢查收據, 提示尚未檢查的新增檔案 | 同一份變更只提醒一次, 不阻擋或重新開啟對話 |

收據按 client、工作階段及實際 worktree 隔離, 只保存內容雜湊與檢查狀態
不讀取對話紀錄、提示或金鑰, 不保存 diff 內容, 不執行 profile 或工具輸入中的命令
新檔、產品行為、測試與驗收仍使用專案選定的檢查, 空白檢查不宣告這些項目通過
Shell 或 MCP 寫入可能沒有觸發 PostToolUse, Stop 會提示已追蹤差異缺少本輪收據

## 安裝與更新

先建立 profile, 內容為相對入口與短指引

```json
{
  "schema_version": 1,
  "entries": ["AGENTS.md", "CLAUDE.md", "AI.md"],
  "start_note": "Read applicable instructions and the current project record",
  "stop_note": "Report results, actual checks and actionable gaps"
}
```

從 Toolkit 根目錄預覽, Python 使用該電腦已驗證的執行檔, macOS 通常為 `python3`

```text
python mcp/scripts/install_agent_hooks.py --client codex --client claude --profile /absolute/profile.json --operations /absolute/maintained-operations.md
```

預覽退出碼 0 表示 CURRENT、1 表示有待套用差異、2 表示輸入或衝突問題
檢查目的檔案後, 相同命令加 `--apply`, 再執行預覽確認所有項目 CURRENT
可用 `--codex-home` 與 `--claude-home` 指定兩個獨立設定目錄

安裝器保留其他設定與 Hooks, 更換已管理項目前核對原內容, 差異檔案備份至各 home 的 `managed-agent-hooks/backups/`
核心與 policy 放在帶版本及內容雜湊的目錄, 相同 bytes 不重寫, 已安裝核心若遭修改則停止並保留差異
舊 bundle 與備份保留供還原, 更新過程若失敗會恢復本次已寫且沒有再被修改的檔案
解除套用時先由原生 Hooks 介面停用, 再按 manifest 的精確群組移除對應設定, 不覆蓋整份 home 設定

| 情境 | 設定及啟動 |
| --- | --- |
| Codex Windows | `~/.codex/hooks.json`, 明確 PowerShell EncodedCommand, 參數保留空白、中文與單引號 |
| Codex macOS | `~/.codex/hooks.json`, POSIX 引號與該電腦 Python 路徑 |
| Claude Windows | `~/.claude/settings.json`, `command` + `args` 直接啟動 Python |
| Claude macOS | 同一組 exec-form 設定, 由目的電腦解析 Python / Git |

每台電腦重新執行安裝器, 不複製另一台電腦產生的絕對路徑或原生設定
Claude 需要支援 exec-form Hooks 的版本, Codex 需要具備目前 Hooks 設定與信任介面的版本
Codex 安裝後用 `/hooks` 或 Desktop Settings > Hooks 審閱並信任三個新定義, 更新定義後重新審閱
不使用跳過 Hook 信任的參數, 既有 `notify`、權限管理與登入設定保留
Claude 在新工作階段以 `/hooks` 核對, 各產品的載入與事件觸發分別驗證

## 驗證與維護

```text
python -B -m unittest discover -s mcp/tests -p test_agent_hooks.py -v
```

安裝後以維護中的驗證入口執行三個命令, `--cwd` 指定要檢查的專案或工作區

```text
python mcp/scripts/verify_agent_hooks.py --client codex --home /absolute/.codex --cwd /absolute/workspace --codex-cli /absolute/codex
python mcp/scripts/verify_agent_hooks.py --client claude --home /absolute/.claude --cwd /absolute/workspace
```

Codex 選用的 `--codex-cli` 會啟動短暫 app-server 呼叫唯讀 `hooks/list`, 完成即關閉, 不建立聊天或呼叫模型
命令執行、原生探索與信任狀態分別輸出, `untrusted` 需在原生介面審閱後才會隨事件執行

測試使用合成 Git 儲存庫, 涵蓋四種設定轉接、目前 OS 的實際命令、worktree、中文及空白路徑、重複事件、失敗恢復、設定保留與衝突
macOS / Windows 原生測試分開執行, 在其中一端產生另一端設定不等於另一端已執行
原生 client 再確認開始事件的短索引、編輯後的失敗提示、Stop 不造成延長對話, 然後保留實際結果於原工作記錄

官方格式: [Codex Hooks](https://learn.chatgpt.com/docs/hooks)、[Claude Code Hooks](https://code.claude.com/docs/en/hooks)
