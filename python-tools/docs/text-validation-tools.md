# 文字與驗證工具

## `text/token_count.py`

使用 [OpenAI tiktoken](https://github.com/openai/tiktoken) 在本機精確計算 BPE Token, 預設編碼 `o200k_base`, 可選 `cl100k_base` 等 tiktoken 支援的編碼, 核心函式 `count_text(text, encoding_name)` 與 `count_file(path, encoding_name)` 可由其他 Python 程式直接呼叫

Codex 按需求選用的入口為 [Token Count Skill](../../skills/token-count/SKILL.md), 收錄於文件與規格處理 Plugin, Plugin 打包相同核心與專用相依清單, 不另維護計算實作

### 安裝與使用

在 `python-tools/` 建立本機環境, 只安裝此工具需要的相依套件, Windows 啟動檔會優先使用 `.venv`

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r setup/requirements-token-count.txt
.\launch-cli.cmd token-count --text "要計算的文字"
.\launch-cli.cmd token-count --input ".\貼上的文字 (1).txt"
.\launch-cli.cmd token-count --input ".\prompt.md" --output ".\tokens.json"
.\launch-cli.cmd token-count --input ".\a.txt" ".\b.md" --output ".\tokens.txt"
.\launch-cli.cmd token-count --text "hello world" --encoding cl100k_base --json
```

macOS 或 Linux 使用 `python launch-cli.py token-count ...`, 需先在相同 Python 環境安裝 `setup/requirements-token-count.txt` 的相依套件

`--input` 與 `--text` 互斥, 都未提供時讀取 UTF-8 stdin, 互動式終端沒有 pipe 時回傳錯誤, 可從任意工作目錄以啟動檔完整路徑執行, 檔案路徑依目前工作目錄解析

### 彩色 Token 檢視與環境預估

```powershell
.\launch-cli.cmd token-count --text "繁體中文與 emoji 👩‍💻" --html ".\tokens.html"
.\launch-cli.cmd context-budget --project "C:\path\project"
.\launch-cli.cmd context-budget --project "C:\path\project" --active-skill "C:\path\SKILL.md" --tool-schema ".\selected-tools.json" --output ".\budget.json"
```

彩色 HTML 可直接在瀏覽器開啟, 點選 Token 可查看 ID、UTF-8 位元組與位置, 支援 Tab 與 Enter, 字元內跨 Token 的界線以漸層顯示, 每個來源預設顯示前 2000 Token, 完整計數保留於頁面, 可用 `--max-display-tokens` 調整

環境預估需要 Python 3.11+, 分類列出 Global/Project Agent、Skills 探索清單、指定啟用的 Skills/角色、Memory、工具定義與社群系統基礎, 來源日期及公式由 `src/text/context_estimates.json` 保存, 提供工具定義時取代逐項工具估算, `--instruction` 加入明確引用的其他指示, `--content` 加入指定文字, 完整選項與來源方法見 [環境預估](../../skills/token-count/references/context-budget.md)

### 統計格式

終端機顯示來源、編碼、字元數、Token 數、UTF-8 bytes 與字元/Token, `--json` 改用 JSON, `--output` 同時另存結果, `.json` 輸出檔會自動使用 JSON, 其他副檔名預設純文字, 已存在的輸出檔拒絕覆寫, 輸出目錄需先存在

JSON 包含 `results` 陣列與 `total_tokens`, 各筆結果包含 `source`、`encoding`、`method=tiktoken`、`chars`、`tokens`、`utf8_bytes`、`chars_per_token`, 多個來源逐檔計算後加總, 合併文字重新分詞的 Token 數可能不同

UTF-8 BOM 不列入文字, 保留 CRLF、空白與最後換行, `chars` 使用 Python Unicode code point 數量, emoji 可能含多個 code point, `utf8_bytes` 是移除 BOM 後文字的 UTF-8 大小, 空文字為 0 Token, `chars_per_token` 為 `null`, `<|endoftext|>` 等字串視為一般文字計算

只分析提供的文字, PDF、Office 等檔案需先轉成文字, 結果不包含 ChatGPT 或 Codex 的訊息結構、工具定義及未提供的內容, 也不是完整請求的 Context 用量

計算不呼叫 OpenAI API, 不需要 API key, 不將輸入文字傳到網路, 首次使用編碼時 tiktoken 會下載並快取編碼字典, 快取可用後可離線計算, CLI 原始碼版預設放在 `python-tools/tiktoken-cache/`, 可用 `TIKTOKEN_CACHE_DIR` 選擇快取位置, 直接呼叫 Python 核心函式時沿用 tiktoken 的快取設定

缺少套件、編碼不存在、字典下載失敗、來源無效或匯出失敗時回傳 `2`, 不產生估算結果, 成功回傳 `0`

## `text/tokenizer.py`

從單一文字檔, CLI 直接提供的文字或 stdin 計算 token, 優先使用 `tiktoken`, 套件缺少, 編碼不存在或 tokenizer 失敗時, 自動依 ASCII 與非 ASCII 字元比率估算區間

```powershell
python launch-cli.py text.tokenizer --input .\prompt.md
python launch-cli.py text.tokenizer --text "測試 text" --encoding cl100k_base --json
Get-Content .\prompt.md -Raw | python launch-cli.py text.tokenizer
```

`--input` 與 `--text` 互斥, 未提供時讀取 stdin, 互動式終端沒有 pipe 時回傳錯誤

CLI 的 `--ascii-chars-per-token` 與 `--non-ascii-chars-per-token` 必須是大於 0 的有限數, `.env` 對應值無效時顯示警告, 並改用 `4` 與 `2`

精確模式輸出單一 `tokens`, 備援估算模式輸出 `min_tokens`, `mid_tokens`, `max_tokens` 與 `fallback_reason`, 並明確標記 `method=fallback`, 小數比率會直接參與計算, 不會先取整數, 估算值不可當成正式計價依據

結束代碼 `0` 表示計算完成, `2` 表示來源或比率錯誤

## `validation/validation_evidence_index.py`

索引指定目錄下一層的 `run-*/results.json`, 依名稱反向排序, 並輸出每次執行的 started, source, baseline, 結果名稱, 狀態, command, 原因, log 參照與未驗證項目

```powershell
python launch-cli.py validation.validation_evidence_index --root C:\path\validation-runs
python launch-cli.py validation.validation_evidence_index --root C:\path\validation-runs --limit 50
python launch-cli.py validation.validation_evidence_index --root C:\path\validation-runs --current-baseline C:\path\current-baseline.json
```

`--limit` 預設 20 且必須大於 0, 根目錄必須存在, 每份 JSON 會檢查頂層物件, `results` 陣列與各結果物件, 格式錯誤的執行會放入 `errors`, 其他有效執行仍保留在 `runs`

此工具只重整既有驗證證據, 不重新執行 build, test, lint, type check 或瀏覽器測試, 沒有 `run-*/results.json` 時輸出空的 `runs` 陣列

提供 `--current-baseline` 時, 以 workspace core 0.2.0 的 `assess_evidence` 比較明確提供的來源與產物資訊, 不讀取其指向的原始碼或執行 command. 既有結果與狀態保留, 另加 `validity`, 缺少新版 core 時需先更新已安裝的 runtime

Baseline 可包含 `source_revision`、`source_diff_sha256`、`source_files` 路徑與 SHA-256 映射、`artifact_sha256`, 舊證據的 `covered_paths` 與本次的 `affected_paths`. Diff hash 應涵蓋當時未提交變更與未追蹤來源, 只核對 HEAD 不足以證明同一份來源

結果分為 `current`、`outdated`、`partial`、`unverified`: 來源 / 產物 hash 改變為 outdated, hash 相符但缺來源、產物或涵蓋範圍時為 partial, 來源身分不足為 unverified. 局部檔案 hash 相符可支持其明確範圍, 不把其他路徑或時間戳推論為已通過, 證據仍適用也不改變原本測試的 PASS / FAIL

結束代碼 `0` 表示索引完成且沒有格式問題, `1` 表示部分執行格式錯誤但已輸出其他有效結果, `2` 表示根目錄或筆數上限錯誤
