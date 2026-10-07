# Feature task-guide format

For the optional structured decisions input, read [decision records](decision-records.md). It adds source type and replacement relationships without changing the existing required fields.

Use this reference when creating or refreshing a reusable guide for one project feature. The guide carries stable navigation and decision boundaries; specifications, current progress and detailed history retain their own owners.

## Resolve the content

| Section | Evidence to retain |
| --- | --- |
| Title and opening scope | Feature identity, authorized owners, scope and exclusions that materially change execution |
| Read by task | Start specification tasks with relevant current Markdown extractions; retain original page/sheet pointers and make visual or original checks conditional on concrete gaps, conflicts or requested verification; resolve external roots from the active task or project layout |
| Source authority | Which original or confirmed decision governs each topic; distinguish original UI/behavior/API evidence from extraction and implementation evidence, retain unresolved conflicts |
| Work item IDs | Maintained ID registry, project-specific group meanings, allocation rules and preservation of existing identifiers; current item status stays in the registry |
| Implementation boundaries | Feature-specific safeguards, state ownership, interface/error rules and accepted decisions that change implementation choices; omit inherited generic rules |
| Verification | Existing focused checks, coverage limits and when broader checks are needed; commands are instructions, not passing results |
| Documentation and records | The project's actual maintained destinations and update triggers, if established; do not impose progress/history files on a project that does not use them |
| Open items | Explicit unresolved gates or pointers to their maintained decisions; block only dependent behavior |

Do not copy another feature's business fields, role codes, source precedence, directories or special verification harness. A public reusable Skill contains no private project sources. Private project guides stay local unless their release or external transfer is authorized.

Generate concise Traditional Chinese headings, table labels and prose, retaining technical identifiers. The English section keys below are generator fields, not a required output language.

Apply the document-writing rule in `SKILL.md`'s Create or refresh section to guides and snapshots; keep limitations tied to their concrete effect on source coverage, requirements or execution.

## Heading importance and presentation

Keep authorization and essential context in the opening scope. Choose the remaining heading order by what matters for this task: a governing conflict or blocked decision may precede a navigation table, while detailed implementation explanations and recordkeeping can follow the main tables. Use `section_order` to express that choice; omitted headings still appear in their default relative order when they have content. It never removes a populated section.

Within a section, put critical framing before the table, present the table, then add supporting bullets. The documentation-trigger table precedes detailed recordkeeping bullets; the ID group table follows the registry pointer and precedes detailed ID rules. Do not rank a section only because its body happens to be a table or a list.

## Generation and integration

1. Read project evidence and resolve existing Markdown extractions using task/source metadata or pointers, without assuming fixed names, folders or same-stem filenames. Read their relevant sections first. Read screenshots or original sections only when visual evidence, missing/unclear/stale extraction, conflicts or an explicit original-source check requires them; if no usable extraction exists, read the relevant original sections. Keep original authority distinct from reading order and report extraction-only coverage. Confirm scope and resolve any decision essential to the guide. Missing coverage stays explicit; a schema passing validation does not establish requirements.
2. Assemble a local JSON input using the fields below. [task-guide.example.json](../assets/task-guide.example.json) is a fictional order-query example showing the shape, not rules to adopt. The coding agent prepares this input; the user can request the guide in natural language.
3. Resolve the bundled generator relative to the installed Skill and preview or create the output. It uses Python 3.10+ standard library only, accepts UTF-8 with or without a BOM and works without the source repository, a network connection, an API Key or MCP.

```text
python <skill-root>/scripts/create_task_guide.py <input.json> --check
python <skill-root>/scripts/create_task_guide.py <input.json> --dry-run
python <skill-root>/scripts/create_task_guide.py <input.json> --allocate-ids
python <skill-root>/scripts/create_task_guide.py <input.json> --output <project-root>/.codex/agent-guidance/<feature>.md
```

Angle-bracket arguments above denote paths resolved for the current environment; quote paths containing spaces. The helper reads only its supplied JSON and writes only the named new output. It does not scan a project, extract source files, choose requirements or edit `AGENTS.md`. Omitted optional sections are not generated; existing output is rejected, including an identical file. Refresh existing guides with a narrow evidence-based edit instead.

4. Inspect the generated Markdown against its sources and current project state. If the requested scope includes discovery, link it from the relevant project `AGENTS.md` with one loading condition, for example `For order-query work, read .codex/agent-guidance/orders.md`; adapt both trigger and path to the real feature. A normal Markdown file is not automatically loaded merely because it exists.
5. Check the conditional pointer and live source references. For ignored guides use direct readback; report only checks actually run. Creating a guide does not demonstrate application, API or client loading behavior.

## Input fields

The root is a JSON object. Unknown or duplicate properties are rejected to avoid silently discarding supplied content. Text accepts Markdown; leave table pipes unescaped because the generator escapes them, and table newlines become `<br>`. Bullet continuations retain multiline text. The title is a single nonempty line. No placeholder is a confirmed fact.

| Field | Type | Required |
| --- | --- | --- |
| `title` | Nonempty string, such as a real feature name plus task rules | Yes |
| `scope` | Nonempty list of nonempty strings | Yes |
| `read_by_task` | Nonempty list of objects containing exactly `need` and `evidence`, both nonempty strings | Yes |
| `source_authority` | Nonempty list of nonempty strings assigning governing evidence by topic | Yes |
| `path_resolution` | List of nonempty strings describing named roots or portable path resolution | No |
| `implementation_boundaries` | List of nonempty strings | No |
| `verification` | List of nonempty strings | No |
| `documentation` | List of nonempty strings describing maintained records | No |
| `documentation_triggers` | List of objects containing exactly `trigger` and `result`, both nonempty strings | No |
| `closeout` | List of nonempty strings for applicable document/delivery checks | No |
| `open_items` | List of nonempty strings describing unresolved decisions or their maintained locations | No |
| `section_order` | Distinct section keys listed in priority order; unlisted sections retain their default relative order | No |
| `id_rules` | List of nonempty strings describing the project's work-item ID rules | No |
| `work_item_ids` | Declared prefix/serial scheme and allocation input described below | No |

Optional lists may be empty. The script verifies types and shape; it does not resolve the paths written inside prose, validate cited source contents, detect every secret or certify semantic equivalence. The coding agent owns those checks using the real project and authorization.

`section_order` accepts `read_by_task`, `source_authority`, `work_item_ids`, `implementation_boundaries`, `verification`, `documentation` and `open_items`. The opening scope remains before these headings. Without a supplied order, these keys define the default sequence; the coding agent should choose a task-appropriate order rather than treat the default as importance evidence.

## ID creation input and registration

For numeric ID allocation, `work_item_ids` contains exactly these fields:

| Field | Content |
| --- | --- |
| `registry` | Nonempty text locating the project's maintained work-item record |
| `separator` | `-`, `_`, `.` or an empty string, matching the declared project syntax |
| `digits` | Integer from 1 to 12 giving the minimum serial width; serials can grow beyond it |
| `groups` | Nonempty list of objects containing exactly `prefix` and `meaning`; prefixes are unique ASCII letter-leading names using letters, digits or underscores |
| `reserved` | List of all known current, completed, removed and historical IDs for the declared groups; repeated identical references are allowed |
| `items` | List of objects containing `key`, `prefix`, `title` and optionally an existing `id`; keys identify items within this allocation input and must be unique |

Existing `id` values are retained exactly and reserved before new allocation, regardless of item order or title changes. New IDs follow each group's maximum positive serial; gaps are not reused. Corrected IDs and their rows remain in current records; show a fully corrected ID as `~~ID~~`, retain remaining work for partial completion and never substitute another item into its slot. `reserved` also accepts these strikethrough display values and normalizes only their decoration; logical IDs and cross-references retain the original value. An undefined group, incompatible format, duplicate item key/ID or two spellings occupying the same group/serial is rejected. An empty `items` list can describe just the guide's scheme. When the project uses another ID format, omit this object, explain its existing process in `id_rules` and use that process.

`--allocate-ids` prints UTF-8 JSON with `status: proposed`, the registry pointer and assigned items. It writes no files, even when `--output` is present. Normal guide generation includes the scheme and group table, not an item-status snapshot or allocation table. Register the proposed IDs in the authorized current record, rechecking unseen concurrent changes first; neither guide generation nor allocation modifies `registry`. Related-item IDs, source references and split/merge mappings are maintained and checked by the coding agent against that record.

## History snapshots

Use the established history destination and append one concise Chinese record for the authorized document trigger. The title time is `yyyy-mm-dd hh:mm`, using the active user/task timezone. The helper requires an explicit timestamp rather than guessing from its host. The coding agent confirms that time and the source evidence before writing; the [fictional history example](../assets/history.example.json) demonstrates format only.

```text
python <skill-root>/scripts/record_history.py <entry.json> --check
python <skill-root>/scripts/record_history.py <entry.json> --dry-run
python <skill-root>/scripts/record_history.py <entry.json> --output <history.md>
```

| Field | Content |
| --- | --- |
| `timestamp` | Required real date/time string in `yyyy-mm-dd hh:mm`, to minute precision |
| `title` | Required short Chinese single-line title |
| `summary` | Required concise Chinese change/decision description |
| `commit` | Optional already-confirmed unique short Git SHA, 4-39 hex characters; do not truncate a full SHA without checking uniqueness |
| `repository` | Optional project name used with a commit as `Git: project@short-sha` |
| `uncommitted` | Optional boolean; when a confirmed base commit is present, adds `+ 未提交變更` |
| `checks` | Optional list of concise actual checks and their limitations |
| `open_items` | Optional list of material remaining work, retaining its original work-item IDs |

Without `commit`, no Git line is generated, even when the project name is supplied. Git absence does not stop recording. The helper does not inspect Git, verify commit uniqueness, certify validation results or infer that a SHA covers a working tree. Preserve those distinctions in the source-backed summary.

When a commit is supplied, `summary` remains mandatory and describes its actual relevant changes, verified against the commit diff; recording just its short SHA or repeating a vague commit message is insufficient. If the record also covers uncommitted work, identify that portion separately in the summary and verification limits.

Writing creates the named Markdown when absent, or appends to its existing UTF-8 bytes while retaining BOM and CRLF/LF convention. Existing entries are not reformatted or rewritten; an identical timestamp/title is rejected to prevent duplicate replay. Read/recheck the record and coordinate one writer when other owners are active; this is not a distributed lock or a global history registry.
