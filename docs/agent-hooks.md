# Claude / Codex 共用 Hooks

版本 0.6.0, 需要 Python 3.11 以上與 Git
共用核心為 `mcp/scripts/agent_hooks.py`, 安裝入口為 `mcp/scripts/install_agent_hooks.py`
個人選項放在工具來源以外的 JSON profile, 執行時不依賴原 checkout

| 事件 | 行為 | 輸出 |
| --- | --- | --- |
| SessionStart | 找出 Git 根目錄、分支與 profile 指定且實際存在的入口, 壓縮後重新提供索引並附上 `compact_note`, 選用時加一行環境摘要 | 最多 1,600 個字元, 同工作階段相同索引略過 |
| UserPromptSubmit | 選用 `delivery_note` 時才登記, 提示以 `cp`、`cpt`、`cpr` 開頭且不超過 200 字元時, 帶入交付約束與 repo 中實際存在的政策檔 | 額外上下文 |
| PreToolUse | 選用 `guards` 時才登記, 在 Bash 與檔案編輯執行前檢查提交身分、AI 共同作者與產生檔案 | 違規時回傳 deny 與原因, 其他呼叫安靜通過 |
| PostToolUse | Edit / Write / MultiEdit / apply_patch 後, 啟用專案檢查時也包含 Bash, 對有變化的已追蹤 diff 執行 `git diff --check`, 選用 `doc_lint` 時另以 textlint 檢查含中文的 Markdown | 成功安靜, 失敗提示位置 |
| SubagentStart | 選用 `subagent_note` 時才登記, 把同一段約束交給每個子代理 | 子代理的額外上下文 |
| PreCompact | 只登記於 Claude, 選用 `compact_note` 時以純文字提供壓縮摘要要保留的項目與現有入口 | stdout 純文字 |
| InstructionsLoaded | 只登記於 Claude, 選用 `instruction_log` 時記錄載入的 `CLAUDE.md` 與 rules 路徑、範圍、原因與 SHA-256 | 只寫收據, Claude 不顯示輸出 |
| ConfigChange | 只登記於 Claude, 選用 `config_change_note` 時記錄變更的設定來源 | 下一次 Stop 提醒一次 |
| Stop | 核對目前 diff 是否有本工作階段的空白檢查收據, 提示尚未檢查的新增檔案 | 同一份變更只提醒一次, 不阻擋或重新開啟對話 |

收據按 client、工作階段及實際 worktree 隔離, 只保存內容雜湊與檢查狀態
預設不讀取對話紀錄, 不保存 diff 內容, 不執行 profile 或工具輸入中的任意命令
新檔、產品行為、測試與驗收仍使用專案選定的檢查, 空白檢查不宣告這些項目通過
Shell 或 MCP 寫入可能沒有觸發 PostToolUse, Stop 會提示已追蹤差異缺少本輪收據

## Codex 每輪原生用量

profile 可選擇加入 `"codex_token_usage": true`, 預設關閉, 只適用於 Codex
Stop 以純 Python 讀取原生用量收據並顯示本輪總 token, 不呼叫模型或網路, 不需要 tiktoken 或 API key
輸入與輸出取自原生計數器, 快取輸入已包含在輸入內, 不再加進總量

```text
Codex 本輪用量: 總計 80 tokens (輸入 70, 輸出 10, 快取輸入 50)
```

安裝器將目前 Codex home 的 `sessions/` 寫入受管 policy, 只接受該目錄內的絕對 `.jsonl` 路徑
核心核對 session_id、turn_id、最終回覆及其後的 token_count, 以本輪前後 total_token_usage 的差額統計多次模型請求, 並檢查各次增量與 last_token_usage 相符
同一回合只顯示一次, 沒有 Git 儲存庫也可顯示, 既有空白檢查與新檔提醒保持原行為
用量收據放在 `managed-agent-hooks/state/usage-<hash>.json`, 只保存版本與數值, 不保存提示、回覆或 transcript 內容

目前支援已核對的 session_meta、task_started、final_answer 與 token_count 記錄格式, transcript 並非穩定的公開介面, 見 [官方輸入欄位](https://learn.chatgpt.com/docs/hooks#common-input-fields)
讀取範圍限制為 transcript 尾端 16 MiB、單筆相關記錄 2 MiB, 另核對第一筆工作階段識別
缺少 transcript、收據尚未寫完、格式不符、計數器重設、回合不符或無法證明完整時不顯示用量, 不輸出部分總量或估算值
例如 ephemeral 工作階段可能沒有 transcript, 這不影響其他 Hooks
統計透過 systemMessage 顯示於原生介面或事件串流, 不要求模型延長回合或改寫已完成的回覆

## 執行前防護

profile 的 `guards` 選擇 PreToolUse 規則, 只用 repository identity 判斷, 不寫入裝置路徑, Windows 與 macOS 使用同一份設定

```json
"guards": {
  "identity": {"owners": ["https://github.com/<owner>"], "email": "<personal commit email>"},
  "ai_coauthor": true,
  "generated": [{"repository": "https://github.com/<owner>/<distribution>", "allow": ["AGENTS.override.md", ".codex/*"]}]
}
```

| 規則 | 拒絕條件 |
| --- | --- |
| `identity` | origin 屬於 `owners` 的 repo 以其他 email 提交, 或其他 repo 沒有 repository-local `user.email`, 改用全域的個人身分 |
| `ai_coauthor` | 提交命令含 Claude、Codex、ChatGPT、OpenAI、Anthropic、Copilot 或 GPT 的 Co-Authored-By trailer |
| `generated` | 在指定散布 repo 以 Edit、Write、MultiEdit、NotebookEdit 或 apply_patch 修改 `allow` 以外的檔案 |

規則命中時在兩端都 deny, 使用者自己在終端機執行的命令不經過 Hooks
Bash 依 `&&`、`||`、`;`、`|` 與換行拆段, 追蹤 `cd` 與 `git -C`, 從檔案讀取的提交訊息與 Shell 間接呼叫不在範圍內
防護是編輯前的提醒邊界, 不是完整權限控制, 遠端的 Secret scanning、Push protection 與分支保護仍各自設定

`"session_environment": true` 在 SessionStart 加一行作業系統、架構、Python 版本與 PATH 上的 Python 指令名稱, 選用 `identity` 時另標示 repo 是否屬於個人
`subagent_note` 是 400 字元內的子代理約束, 例如精簡英文、只處理委派範圍與不自行提交或安裝, 由 SubagentStart 交給每個子代理

## 工作階段輔助

| profile 欄位 | 用途 | 平台 |
| --- | --- | --- |
| `delivery_note`、`delivery_entries` | 交付關鍵字帶入 400 字元內的約束, `delivery_entries` 列出 repo 相對路徑, 只回報實際存在的檔案 | Codex、Claude |
| `compact_note` | 1,000 字元內的壓縮重點, 例如保留原始需求、決定、權限、檔案、提交與待驗收, Claude 壓縮前由 PreCompact 當成摘要指示, 兩端壓縮後再由 `source: "compact"` 的 SessionStart 補進上下文 | Codex、Claude, Codex 沒有自訂壓縮提示的設定, 只用壓縮後的補充 |
| `doc_lint` | 編輯含中文的 Markdown 後執行 textlint, 每份內容只檢查一次, 單檔 1 MiB 內、每次最多 5 份 | Codex、Claude |
| `instruction_log` | 記錄指示檔實際載入, 收據在 `managed-agent-hooks/state/instructions-<hash>.json`, 只保存路徑、範圍、原因與雜湊 | Claude |
| `config_change_note` | Claude 會丟棄 ConfigChange 的訊息, 因此先記錄來源, 在同一工作階段的下一次 Stop 提醒讀回設定 | Claude |

`doc_lint` 在執行時尋找 Toolkit 開發工具安裝器的 npm 位置, macOS 為 `~/Library/Application Support/codex-setup/tools/npm`, Windows 為 `%LOCALAPPDATA%/codex-setup/tools/npm`, 使用其中的 textlint 與 `proofreading/zh-tw/.textlintrc.cjs`, profile 不保存裝置路徑
找不到 textlint 或 Node 時, 同一工作階段只提示一次, 專案自有的 textlint 設定仍依專案原流程執行

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
Codex 安裝後用 `/hooks` 或 Desktop Settings > Hooks 審閱並信任新定義, 數量依 profile 選用的事件而定, 更新定義後重新審閱
不使用跳過 Hook 信任的參數, 既有 `notify`、權限管理與登入設定保留
Claude 在新工作階段以 `/hooks` 核對, 各產品的載入與事件觸發分別驗證

## 驗證與維護

```text
python -B -m unittest discover -s mcp/tests -p "test_agent_hook*.py" -v
```

安裝後以維護中的驗證入口執行三個命令, `--cwd` 指定要檢查的專案或工作區

```text
python mcp/scripts/verify_agent_hooks.py --client codex --home /absolute/.codex --cwd /absolute/workspace --codex-cli /absolute/codex
python mcp/scripts/verify_agent_hooks.py --client claude --home /absolute/.claude --cwd /absolute/workspace
```

Codex 選用的 `--codex-cli` 會啟動短暫 app-server 呼叫唯讀 `hooks/list`, 完成即關閉, 不建立聊天或呼叫模型
每次驗證使用獨立工作階段識別, JSON 分開回報 command、json_output、output_kind、hook_output, project_checks 與 native_event 保持 not_verified
空輸出可能是略過或去重, 提示內容可能是檢查失敗, 外層結束碼 0 不代表專案測試通過
命令執行、原生探索與信任狀態分別輸出, `untrusted` 需在原生介面審閱後才會隨事件執行

手動送入事件只驗證命令及回傳格式, 不等於用戶端已自動觸發事件
使用實際專案示範時, 在隔離 clone 與獨立狀態目錄操作, 寫入前用 `git ls-files --error-unmatch <path>` 確認已追蹤路徑, 保留預期值、實際值與收據

測試使用合成 Git 儲存庫, 涵蓋四種設定轉接、目前 OS 的實際命令、worktree、中文及空白路徑、重複事件、失敗恢復、設定保留與衝突
macOS / Windows 原生測試分開執行, 在其中一端產生另一端設定不等於另一端已執行
原生 client 再確認開始事件的短索引、編輯後的失敗提示、Stop 不造成延長對話, 然後保留實際結果於原工作記錄

官方格式: [Codex Hooks](https://learn.chatgpt.com/docs/hooks)、[Claude Code Hooks](https://code.claude.com/docs/en/hooks)

## 專案檢查與公開內容防護

`project_checks.py` 共用核心提供三項能力, 私人 registry 依 repository identity 設定公開範圍、路徑選擇與交付參考
安裝時加 `--projects <registry.json>` 及每份 checkout 的 `--checkout <root>`, 核對 Git origin 後綁定本機路徑, 未選定的 checkout 不執行專案檢查

| 能力 | 行為與證據 |
| --- | --- |
| 公開內容 | 檢查完整 Git index 路徑與有變更的 staged blobs, 使用既有公開內容核心辨識私鑰, 只回報物件識別與原因, 不輸出內容 |
| 輕量檢查 | 依變更路徑選 JSON/TOML 解析、Python AST 或 Node `--check`, 不匯入產品模組、不修檔、不安裝相依套件 |
| 證據核對 | 收據綁定 client、session、checkout、規則、runtime 與輸入摘要, 內容變化、失敗、缺少 runtime、逾時均不算通過 |

Lifecycle 每次提供 6 秒的語法檢查預算, CLI 提供 60 秒, 每檔最多 4 MiB, 每組最多 64 MiB, 變更路徑最多 1,000 筆
超出限制保留 deferred/error, CLI 可重跑 deferred/unavailable, 不把部分檢查當作完成
Node 語法檢查不繼承 NODE_OPTIONS / NODE_PATH, Python 只建立 AST, 不產生 pycache
JSONC、框架型別、規則語意、產品測試與視覺驗收依專案原關卡執行
收據不保存原始程式碼、對話或命令輸出, Stop 同一份提示只顯示一次並避開 stop_hook_active

以安裝 manifest 的 bundle 找到 `policy.json` 與 `project_checks.py`, 執行:

```text
python <bundle>/project_checks.py run --policy <bundle>/policy.json --state-dir <state> --cwd <checkout>
python <bundle>/project_checks.py audit --policy <bundle>/policy.json --state-dir <state> --cwd <checkout>
python <bundle>/project_checks.py public-index --policy <bundle>/policy.json --state-dir <state> --cwd <checkout>
```

run / audit 預設使用同一個 delivery session, 可用 `--session` 指定本次識別
CLI 結束碼 0 只代表所列檢查, 1 表示失敗或證據缺漏, 2 表示檢查無法完成
`project_acceptance` 保留 not_verified, delivery 欄列出原專案仍需核對的關卡, 不接受呼叫者直接填入 PASS

公開專案另以 `install_project_checks.py --policy <bundle>/policy.json --state-dir <state> --checkout <root>` 預覽 Git hook 安裝, 核對後加 `--apply` 並重跑預覽
此入口把 dispatcher 放在 Git metadata, 備份原設定, 保留既有 Hooks 並串接執行, 不把個人 registry 寫進公開工作樹
pre-commit 先執行原 Hook, 再檢查實際 index, pre-push 等其他既有 Hook 保留原參數與 stdin
原 Hook 沒有啟用時不擅自啟用儲存庫中另一組 Hooks, 未管理的本機差異會阻止覆寫
新關卡不掃描整份歷史, 既有歷史關卡與 CI 維持原規範, Git 的略過選項仍可略過本機 Hooks
還原時先核對 managed-project-checks/manifest.json 的 original 與 original_directory, 只還原 core.hooksPath 的原值, 其他 Git 設定維持現況, 保留備份與收據

## 採用的外部方法

2026-11-04 核對官方文件與原始社群專案, 採用方法而不安裝外部 Hook 套件

| 來源 | 採用與調整 |
| --- | --- |
| [Claude 官方指南](https://code.claude.com/docs/en/hooks-guide) | 事件依用途分工、工具 matcher、stop_hook_active 防迴圈, 保留本機檢查與原生事件驗收的區別 |
| [Codex Hooks](https://learn.chatgpt.com/docs/hooks) | 使用支援的事件與輸出, 設定更新後另核對探索與信任 |
| [lint-staged](https://github.com/lint-staged/lint-staged) | 採路徑選擇與 staged 內容觀念, 本流程直接讀 Git index, 不進行 stash、暫存重寫或自動修正 |
| [agent37 file-guard](https://github.com/agent37-platform/claude-code-hooks/blob/main/hooks/file-guard.py) | 敏感路徑分類與精確例外, 本流程的阻擋點放在 Git pre-commit |
| [edgeless verify-completion](https://github.com/edgeless-ai/claude-code-hooks#verify-completion) | 採交付前核對證據的用途, 不採完成字眼或輸出中的測試數字判定, 改用本機輸入摘要與檢查結果 |

來源描述不等於本機驗收, 官方與社群版本更新後依受影響事件重新核對
