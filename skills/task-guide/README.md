# Task Guide

Create feature-specific navigation, work-item ID rules and concise Taiwan Traditional Chinese history from actual project sources and confirmed decisions. The order-query feature, IDs, SHA and timestamps below are fictional format examples.

## Installation

Copy the complete `task-guide/` folder into the client's active Skills directory, including `SKILL.md`, `README.md`, `agents/openai.yaml`, `assets/`, `references/` and `scripts/`. Back up and compare an existing version before replacement; the repository is source and the installed copy is a mirror.

Windows/macOS use the same Skill. Scripts require Python 3.10+ standard library, without MCP, keys or a fixed checkout. Use the actual `python` or `python3` executable and quote paths containing spaces. Without Python, the agent may edit the guide directly and report that the generator was not run.

## Request a guide

| Need | Behavior |
|---|---|
| New feature guide | Identify project, feature and sources; verify evidence before writing the requested path or `.codex/agent-guidance/<feature>.md` |
| Work-item IDs | Read the existing method guide/approved persistent issuance source and continue above each prefix's highest issued serial, even when its last row was removed |
| Record IDs | Use one to three English letters by record complexity plus a serial, such as `X-1`, `UI-12`, `API-3`; zero padding is optional, calculation/formula labels may use `X`, `Y`, `Z` alone |
| Resolved items | Follow explicit task/project decisions; this decision removes issue/maintenance rows into concise history, keeps progress/reference IDs and preserves unfinished work/check gaps |
| History | Use concise Taiwan Traditional Chinese and minute-resolution timestamps; include a short SHA plus actual committed changes when confirmed, otherwise record directly |

A reusable request:

```text
Use $task-guide to create an order-query guide from this project's AGENTS.md, implementation, confirmed decisions and specified sources.
Locate matching Markdown extracts by current task/source metadata and read relevant sections first. Check screenshots or originals only for visual evidence, missing/unclear/stale extracts, conflicts or an explicit original-source check. Preserve original authority; without usable extracts read relevant originals without unrequested extraction work.
Resolve scope and source authority. Order sections by importance: essential conclusions/blockers first, main tables next, detailed bullets afterward. AI-facing guides use concise English and retain unresolved decisions. English headings are the new default; use `--language zh-TW` for explicitly requested human Chinese output. Supplied source wording and IDs remain unchanged.
Preserve existing IDs without filling gaps, renumbering or reuse. For new records choose one to three English letters by complexity plus a serial; zero padding is optional, calculation/formula labels may use letters alone. Follow explicit task/project decisions: this decision removes resolved issue/maintenance rows after concise history records their original problem, solution, source/version and checks/gaps, while progress/reference indexes retain IDs. Allocate above each prefix's persistent highest-issued value, record its source/usage in the existing method guide and update/read back it on registration; never infer it from remaining current rows.
Keep current state, methods and history separate. Update history only for material changes under the requested/established trigger, choosing useful fields from that round. Use yyyy-mm-dd hh:mm with the user/task timezone when recording time. Record verified Git changes and actual check limits. For a requested restart, first preserve the complete old edition in ZIP and compare extracted bytes, then write concise new history with ordinary Markdown headings and updated navigation.
```

## Layout and source navigation

An example order is opening scope, source authority, blocking decisions, task-to-source navigation, ID registry, then implementation/check/document details. Choose `section_order` by the task's priorities, not by whether content is a table or list; see [format and tools](references/task-guide.md).

Start field/interaction work with matching specification extracts, and API mapping with relevant operation extracts. Follow original page/sheet pointers when a concrete gap, conflict or requested check requires it. Extracts need no fixed name or folder; extraction-only reading does not establish original-source verification.

## ID preservation

| Display ID | Example | State |
|---|---|---|
| UI-01 | Query area | Partially complete, remaining work retained |
| UI-08 | New conditional interaction | Continue above persistent issued high-water 07 |
| API-03 | Response mapping | Continue after recorded maximum 02 |

This is a current issue view: resolved `UI-07` is absent, its original problem/solution remain in concise history, and the existing method guide retains highest issued `UI: 7` with its issuance/history source. `UI-08` follows that persistent value; deleting the last current row never resets it. Progress tables and API/endpoint reference indexes retain IDs under this decision, while other explicit project policies remain available. See [issued-ID high-water source](references/task-guide.md#issued-id-high-water-source) for the existing helper's reservation input and registration guard.

From the Skill root, preview [example input](assets/task-guide.example.json):

```text
python scripts/create_task_guide.py assets/task-guide.example.json --dry-run
python scripts/create_task_guide.py assets/task-guide.example.json --allocate-ids
```

Allocation returns proposals, not automatic persistent writes. One owner reads the recorded high-water source, supplies its reservations, then updates and reads back the value when registering issued IDs. The counter records issuance, not completion status.

## History examples

The following fictional localized artifacts illustrate output. A confirmed commit records its SHA and concrete changes, with uncommitted work separate. Select useful fields for each material change; detailed archive checks and hash inventories stay in evidence/metadata. Restart rules are linked from [document views](references/documentation-views.md).

```markdown
## 2026-10-01 10:05 查詢欄位驗證

Git: example@abcdef1234 + 未提交變更

時區: Asia/Taipei

UI-07 原問題為不合法格式仍可送出, commit 加入格式檢核與錯誤提示, 問題列移出現況, ID 與解法留本歷史, 相關功能進度與 API 索引保留 ID, 方法指引保留 UI 最高已發行序號 7, 未提交部分新增 UI-08 條件連動待辦

- 驗證: 欄位格式 focused Test 通過, 正式 API 未驗證
- 未完成: UI-08 條件連動, API-03 mapping 核對
```

Without a commit, omit the Git line:

```markdown
## 2026-10-01 10:10 盤點查詢待辦

時區: Asia/Taipei

新增 UI-08 與 API-03 待辦, UI-07 原問題與解法留既有歷史, 發號依方法指引中的最高已發行序號 UI: 7、API: 2, 來源為原發行/歷史紀錄, 尚未實作

- 驗證: 僅文件與編號核對, 未執行 application Test
```

Preview [uncommitted](assets/history.example.json) and [committed](assets/history-commit.example.json) inputs; replace examples with actual timestamp, diff and checks before writing:

```text
python scripts/record_history.py assets/history.example.json --dry-run
python scripts/record_history.py assets/history-commit.example.json --dry-run
```

Add `--output <history.md>` to create/append a snapshot. Existing text/newlines are preserved and duplicate timestamp/title entries are not appended. Supply the user/task timezone rather than assuming the execution host's zone.
