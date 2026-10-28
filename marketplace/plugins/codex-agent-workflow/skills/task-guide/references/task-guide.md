# Feature task-guide format

For the optional structured decisions input, read [decision records](decision-records.md). It adds source type and replacement relationships without changing the existing required fields.

Use this reference when creating or refreshing a reusable guide for one project feature. The guide carries stable navigation and decision boundaries; specifications, current progress and detailed history retain their own owners.

## Resolve the content

| Section | Evidence to retain |
| --- | --- |
| Title and opening scope | Feature identity, authorized owners, scope and exclusions that materially change execution |
| Read by task | Start specification tasks with relevant current Markdown extractions; retain original page/sheet pointers and make visual or original checks conditional on concrete gaps, conflicts or requested verification; resolve external roots from the active task or project layout |
| Source authority | Which original or confirmed decision governs each topic; distinguish original UI/behavior/API evidence from extraction and implementation evidence, retain unresolved conflicts |
| Work item IDs | Existing method guidance/approved issuance source, project-specific groups, persistent highest-issued serials and stable IDs; status stays in current progress/issue views |
| Implementation boundaries | Feature-specific safeguards, state ownership, interface/error rules and accepted decisions that change implementation choices; omit inherited generic rules |
| Verification | Existing focused checks, coverage limits and when broader checks are needed; commands are instructions, not passing results |
| Documentation and records | The project's actual maintained destinations and update triggers, if established; do not impose progress/history files on a project that does not use them |
| Open items | Explicit unresolved gates or pointers to their maintained decisions; block only dependent behavior |

Do not copy another feature's business fields, role codes, source precedence, directories or special verification harness. A public reusable Skill contains no private project sources. Private project guides stay local unless their release or external transfer is authorized.

AI guides use concise English narrative, headings and table labels. English renderer labels are the default; `--language zh-TW` retains the former Chinese layout for explicitly requested human output. JSON keys, IDs and supplied literal source text do not change. The renderer does not translate supplied content.

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

For new document records, select one to three English letters by complexity and append a numeric serial, such as `X-1`, `UI-12` or `API-3`; zero padding is optional. Existing identifiers stay stable. Calculation conditions, variables or formula labels may use letters alone, such as `X`, `Y`, `Z`, preserving the actual mathematics. Letter-only labels use direct Markdown or `id_rules`; the numeric allocator does not allocate them.

### Issued-ID high-water source

Record each prefix's highest-issued serial or equivalent persistent issued-ID evidence in the project's existing method guide or approved tracking location. Identify the maintained location, prefix/value, supporting issuance/history source and how the allocator reads it; retain no duplicate completion status. Progress records and API/endpoint reference indexes retain their IDs, while this decision removes resolved issue/maintenance rows after concise history preserves their problem, solution, source/version and checks/gaps. Explicit task/project decisions choose retention/removal; the user's current decision takes precedence.

For illustration, a method guide can retain `UI: highest issued 7, source: UI-07 registration/history, allocator reservation: UI-07` even after that row leaves current issues. The next issue is `UI-8` when the chosen format is unpadded, not the remaining list's maximum plus one. Do not fill gaps, renumber or reuse old IDs. References and history remain reachable from the existing index; growing records are not forced into one current-state file.

Before issuance, one owner reads the latest persistent value and relevant current/history evidence, reconciles any higher issued serial and uses the existing revision/write guard. Missing or conflicting issuance evidence blocks new IDs until resolved; zero is valid only for a confirmed unused prefix. On actual registration, persist the new highest-issued value with its source and read it back. Preview proposals do not update the counter; removed rows never lower it.

The existing numeric helper takes supplied reservations, not a persistent store. Populate `reserved` from the maintained issued-ID record or at least the highest issued ID for every used prefix, alongside other known reservations. Record that source and usage in `id_rules`/the method guide. Never pass only remaining current IDs or infer that `--allocate-ids` has registered them. Preserve the exact historical ID spelling when using a high-water reservation.

For numeric ID allocation, `work_item_ids` contains exactly these fields:

| Field | Content |
| --- | --- |
| `registry` | Nonempty text locating maintained work records and their existing persistent issuance source |
| `separator` | `-`, `_`, `.` or an empty string, matching the declared project syntax |
| `digits` | Integer from 1 to 12 giving the minimum serial width; serials can grow beyond it |
| `groups` | Nonempty list of objects containing exactly `prefix` and `meaning`; prefixes are unique ASCII letter-leading names using letters, digits or underscores |
| `reserved` | Reservations from the persistent issued-ID/high-water source plus other known IDs, including removed/history IDs; never only remaining current rows; identical repeats are allowed |
| `items` | List of objects containing `key`, `prefix`, `title` and optionally an existing `id`; keys identify items within this allocation input and must be unique |

Existing `id` values are retained exactly and reserved before new allocation, regardless of item order or title changes. New IDs follow the maximum supplied issued-ID reservations for each group; the caller supplies the persistent high-water evidence above. Current rows may be removed under their explicit policy without removing issuance reservations. The helper also accepts historical `~~ID~~` decoration and normalizes only that display; logical IDs stay unchanged. An undefined group, incompatible format, duplicate item key/ID or two spellings occupying the same group/serial is rejected. An empty `items` list can describe only the scheme. For another established ID format, retain its process in `id_rules` instead of forcing this allocator.

`--allocate-ids` prints UTF-8 JSON with `status: proposed`, the registry pointer and assigned items. It writes no files, even when `--output` is present. Normal guide generation includes the scheme and group table, not an item-status snapshot or allocation table. Register the proposed IDs in the authorized current record, rechecking unseen concurrent changes first; neither guide generation nor allocation modifies `registry`. Related-item IDs, source references and split/merge mappings are maintained and checked by the coding agent against that record.

## History snapshots

Use the established history destination and append one concise Chinese record for the authorized document trigger. The title time is `yyyy-mm-dd hh:mm`, using the active user/task timezone. The helper requires an explicit timestamp rather than guessing from its host. The coding agent confirms that time and the source evidence before writing; the [fictional history example](../assets/history.example.json) demonstrates format only.

Select history fields by the material change and intended reader. The JSON fields below describe this optional helper, not a closed list for human history. Use direct Markdown for other useful fields/layouts, include timezone when recording time, and follow [document views](documentation-views.md) for a requested archive-first restart. The helper only appends; it does not archive or verify an old edition.

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
