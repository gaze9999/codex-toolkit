# Work Artifact Cleanup 開發產物清理

掃描可丟棄的開發快取與中間產物, 預設只產生預覽清單, `--apply` 才移到可復原的隔離區, `--purge-quarantine` 才永久刪除本工具建立且超過保存天數的隔離批次

## 建置

使用 Rust 1.89 以上版本, 在 Toolkit 根目錄執行

```sh
cargo install --locked --path tools/work-artifact-cleanup
```

安裝後可直接執行 `work-artifact-cleanup`, 也可以不安裝, 改用 `cargo run --locked --release --manifest-path tools/work-artifact-cleanup/Cargo.toml -- <參數>`

## 使用

```sh
work-artifact-cleanup
work-artifact-cleanup --root /path/project --root /path/another
work-artifact-cleanup --root /path/project --include-build --include-work-dirs --apply
work-artifact-cleanup --output-dir /safe/cleanup --purge-quarantine --older-than-days 7
```

| 參數 | 作用 |
| --- | --- |
| `--root [PATH]` | 掃描的資料夾, 可重複, 不給值時使用目前資料夾, 完全不指定時也使用目前資料夾 |
| `--apply` | 把候選移到隔離區, 沒有這個參數時只預覽 |
| `--include-build` | 納入未追蹤的 `build`、`dist` 與 `*.egg-info` |
| `--include-work-dirs` | 納入未追蹤的 `work`、`.work`、`tmp` 與 `temp` |
| `--min-age-days DAYS` | 候選至少多久未修改, 預設 1 天 |
| `--output-dir PATH` | 清單、事件紀錄與隔離區的上層資料夾, 預設 `~/.work-artifact-cleaner` |
| `--purge-quarantine` | 永久刪除本工具建立的舊隔離批次 |
| `--older-than-days DAYS` | 隔離批次保存天數, 預設 7 天 |

天數必須是 0 到 365000 的有限數

預設候選包含 `__pycache__`, pytest、mypy、ruff、tox、nox 快取, `htmlcov`, coverage 與常見暫存檔

## 安全檢查

- 拒絕檔案系統根目錄與不存在的根目錄
- 不進入 Git、Mercurial、Subversion 中繼資料, `.codex`、`logs`、`backups` 或 `quarantine`
- 不跟隨 symlink 資料夾
- 跳過包含巢狀 repository 或 Git 已追蹤內容的候選, Git worktree 使用的 `.git` 檔案也會辨識
- 資料夾以內部最新檔案時間判斷是否達到最低天數
- `--apply` 搬移前會重新檢查巢狀 repository 與 Git 已追蹤內容
- `--purge-quarantine` 只刪除含 `.my-py-tools-quarantine.json` 擁有者標記的批次, 先前 Python 版建立的批次也可清除, 使用者自行放入的資料夾不處理

## 輸出

每次執行在 `<output-dir>/logs/cache-cleanup-<時間>/` 寫入 `manifest.json` 或 `result.json` 與 `cleanup.jsonl` 事件紀錄, 隔離批次放在 `<output-dir>/quarantine/cache-cleanup-<時間>/`

| 結束碼 | 意義 |
| --- | --- |
| `0` | 預覽、隔離或永久清除完成 |
| `2` | 參數錯誤, 安全檢查, I/O 或 Git 查詢失敗 |

## 驗證

```sh
cargo test --locked --manifest-path tools/work-artifact-cleanup/Cargo.toml
cargo clippy --locked --manifest-path tools/work-artifact-cleanup/Cargo.toml --all-targets -- -D warnings
```
