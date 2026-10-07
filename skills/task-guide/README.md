# Task Guide

Create feature-specific navigation, work-item ID rules and concise Taiwan Traditional Chinese history from actual project sources and confirmed decisions. The order-query feature, IDs, SHA and timestamps below are fictional format examples.

## Installation

Copy the complete `task-guide/` folder into the client's active Skills directory, including `SKILL.md`, `README.md`, `agents/openai.yaml`, `assets/`, `references/` and `scripts/`. Back up and compare an existing version before replacement; the repository is source and the installed copy is a mirror.

Windows/macOS use the same Skill. Scripts require Python 3.10+ standard library, without MCP, keys or a fixed checkout. Use the actual `python` or `python3` executable and quote paths containing spaces. Without Python, the agent may edit the guide directly and report that the generator was not run.

## Request a guide

| Need | Behavior |
|---|---|
| New feature guide | Identify project, feature and sources; verify evidence before writing the requested path or `.codex/agent-guidance/<feature>.md` |
| Work-item IDs | Read current/history registries and continue after each group's greatest serial |
| Resolved items | Keep the original row/ID, strike through only fully resolved IDs and retain unfinished work for partial completion |
| History | Use concise Taiwan Traditional Chinese and minute-resolution timestamps; include a short SHA plus actual committed changes when confirmed, otherwise record directly |

A reusable request:

```text
Use $task-guide to create an order-query guide from this project's AGENTS.md, implementation, confirmed decisions and specified sources.
Locate matching Markdown extracts by current task/source metadata and read relevant sections first. Check screenshots or originals only for visual evidence, missing/unclear/stale extracts, conflicts or an explicit original-source check. Preserve original authority; without usable extracts read relevant originals without unrequested extraction work.
Resolve scope and source authority. Order sections by importance: essential conclusions/blockers first, main tables next, detailed bullets afterward. Write the guide in concise Taiwan Traditional Chinese and retain unresolved decisions.
Preserve existing IDs and rows. Strike through fully resolved IDs without reassignment/reuse; allocate after each group's current/historical maximum and check the latest registry before registration.
Add history only when requested or required by the established document workflow. Use yyyy-mm-dd hh:mm in the user/task timezone. Record a verified short SHA and actual diff content for a commit, separate uncommitted work, and preserve existing history.
```

## Layout and source navigation

An example order is opening scope, source authority, blocking decisions, task-to-source navigation, ID registry, then implementation/check/document details. Choose `section_order` by the task's priorities, not by whether content is a table or list; see [format and tools](references/task-guide.md).

Start field/interaction work with matching specification extracts, and API mapping with relevant operation extracts. Follow original page/sheet pointers when a concrete gap, conflict or requested check requires it. Extracts need no fixed name or folder; extraction-only reading does not establish original-source verification.

## ID preservation

| Display ID | Example | State |
|---|---|---|
| UI-01 | Query area | Partially complete, remaining work retained |
| ~~UI-07~~ | Resolved field validation | Original row and logical ID retained |
| UI-08 | New conditional interaction | Continue after recorded maximum 07 |
| API-03 | Response mapping | Continue after recorded maximum 02 |

Strikethrough changes display only: `UI-07` remains the logical ID in links/history. Never assign retired IDs or historical gaps to another item; preserve relationships when splitting/merging.

From the Skill root, preview [example input](assets/task-guide.example.json):

```text
python scripts/create_task_guide.py assets/task-guide.example.json --dry-run
python scripts/create_task_guide.py assets/task-guide.example.json --allocate-ids
```

Allocation returns proposals, not automatic registry changes. One registry owner checks current/history state before recording them.

## History examples

The following intentionally localized artifacts illustrate output. A confirmed commit records its SHA and concrete changes, with uncommitted work separate:

```markdown
## 2026-10-01 10:05 完成查詢欄位驗證

Git: example@abcdef1234 + 未提交變更

commit 已完成 UI-07 欄位格式檢核與錯誤提示, 未提交部分新增 UI-08 條件連動待辦, 現況表保留原列並將 UI-07 畫線

- 驗證: 欄位格式 focused Test 通過, 正式 API 未驗證
- 未完成: UI-08 條件連動, API-03 mapping 核對
```

Without a commit, omit the Git line:

```markdown
## 2026-10-01 10:10 盤點查詢待辦

新增 UI-08 與 API-03 待辦, 保留原 ID 與 ~~UI-07~~ 原列, 尚未實作

- 驗證: 僅文件與編號核對, 未執行 application Test
```

Preview [uncommitted](assets/history.example.json) and [committed](assets/history-commit.example.json) inputs; replace examples with actual timestamp, diff and checks before writing:

```text
python scripts/record_history.py assets/history.example.json --dry-run
python scripts/record_history.py assets/history-commit.example.json --dry-run
```

Add `--output <history.md>` to create/append a snapshot. Existing text/newlines are preserved and duplicate timestamp/title entries are not appended. Supply the user/task timezone rather than assuming the execution host's zone.
