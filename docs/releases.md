# 版本與發布

整包版本由根目錄 `VERSION` 管理, Skill、Plugin、`python-tools/VERSION` 與各 Python package 保留各自版本, 同一個整包 Tag 的 manifest 記錄實際元件組合, 不要求套件版本與整包相同

來源基準使用指向已審查 commit 的完整 annotated Tag `vX.Y.Z`, patch 與 minor 都可依交付需求建立, 0.x 表示開發階段, 不禁止 GitHub Release, 1.0.0 仍須符合公開 API 與產品驗收條件

## 來源與下載包

一般 commit / push 不建 Tag, 來源基準交付可停在 Tag, 推送 Tag 不建立 Release 或草稿, 下載包交付才明確啟用下列手動 workflow 的 `publish`, 預設為 false, 所有 workflow 都要求已存在、與整包 `VERSION` 一致的完整 Tag

| Workflow | 資產 |
|---|---|
| `.github/workflows/plugin-release.yml` | 來源映射與 hash 已驗證的 Plugin archives |
| `.github/workflows/cli-release.yml` | Windows x64、macOS arm64 / x64 的 portable CLI 與 checksums |
| `.github/workflows/python-tools-release.yml` | 獨立 Python 來源包、核心 wheel 與三平台 CLI, 使用 Tag 提交內的元件版本 |

先通過必要建置與檢查, 再將資產附加至相同 Tag 的草稿 Release, workflow 不建立 Tag、不自動公開草稿, 拒絕已發布 Release 與重複資產名稱, 寫入同一草稿的 workflow 依序執行

所有必要資產、來源 commit、版本、manifest、SHA-256 與 notices 核對後, 才在當次發布授權內公開完整草稿, 保持已發布 Tag 與資產固定, 本機測試或封裝不取代原生平台 CI

獨立 Python 工具的本機 `scripts.release publish` 保留入口並提示改走上述 CI, 不再直接推送分支或建立 Release, 詳見 [Python 工具交付](../python-tools/docs/releases.md)

[Git Tag](https://git-scm.com/docs/git-tag)、[SemVer](https://semver.org/) 與 [GitHub 草稿發布](https://docs.github.com/en/repositories/releasing-projects-on-github/managing-releases-in-a-repository) 為版本與發布程序的參考來源, 核對日期為 2026-10-15
