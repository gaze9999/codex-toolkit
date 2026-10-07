# Requirement and decision records

Use the generator's optional decisions array only when the user requests durable structured records or the project already maintains them. Track ordinary in-turn steering in task context. Do not save whole conversations, turn counts or redundant status reports.

Each record has id, type, source and summary; supersedes is an optional array of prior IDs retained in the same input. Types are specification (existing authoritative requirement), user_decision (explicit confirmed change) and execution_plan (implementation arrangement without new authority). Keep the actual original page/sheet/section or confirmed decision pointer in source. A parser cannot establish consent or source truth.

IDs remain stable when wording, priority or status changes. Preserve replaced records and sources, use a new ID for a materially new decision, and reconnect affected acceptance/evidence. The helper rejects duplicate IDs, dangling replacement targets and cycles; it derives active/superseded status without rewriting history. An execution plan must not silently override a specification.

The optional section_order key decisions places the table where it helps the task. Existing inputs without decisions retain their existing sections. Use --check or --dry-run for validation/preview; file creation remains explicit and refuses overwrite.
