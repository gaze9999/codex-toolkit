# 版本與交付設定

Toolkit 的整包版本由 `VERSION` 保存, Skill、Plugin 與 Python package 各自管理版本

| 條件 | 交付方式 |
|---|---|
| `cp` | 提交並推送已審查範圍 |
| `cpr`, 整包低於 1.0.0 | 完成驗證、commit / push, 已完成的 minor 階段建立完整版本 Tag |
| 1.0.0 前的 patch | 更新受影響元件並推送, 整包 Tag 依實際交付需求處理 |
| `cpr`, 1.0.0 起 | 依使用者影響及下載包交付需求決定 Tag / GitHub Release |

1.0.0 前的交付使用 Git commit 與必要 Tag, GitHub Release、draft 及 prerelease 在穩定 1.0.0 起使用. Release workflows 檢查完整穩定版本、Tag 與 `VERSION`, 通過後才建置及上傳

相容修正使用 patch, 功能階段使用 minor, 0.x 不相容調整使用 minor 並列升級操作. 1.0.0 起依 [SemVer](https://semver.org/) 管理相容性, 版本數字無一位數限制

Tag 使用 `vX.Y.Z` 並指向已審查、驗證及推送的確切提交, 保留既有 Tag 對應. GitHub Release 資產依來源 manifest、版本及 SHA-256 核對, 所需 README、LICENSE、第三方 notices 與必要 CI 依產物檢查

CLI / MCP 操作、公開核心 API、工具參數及結果、Plugin / Skill 入口與資料格式是相容性判斷範圍. 建置來源及選項見 [安裝包](setup/packages.md)
