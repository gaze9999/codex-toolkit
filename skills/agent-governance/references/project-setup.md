# Set up project instructions

Read when creating or restructuring a project's instruction files or roles.

- Inspect supplied project material, actual source/configuration and existing instructions before choosing a structure. A private setup checkout or fixed source path is not a prerequisite.
- For an authorized setup, select relevant [project starter templates](../assets/project-starter/README.md) from confirmed project/tool facts. Remove placeholders and rules that do not affect decisions; keep always-loaded root/nested files brief.
- Confirm visibility and tracked state before creating project-local instructions, roles or guides. Apply [instruction layering and exact Git exclusions](instruction-layering.md#project-local-visibility-and-git-storage): public local guidance defaults to local exclusion, private portable guidance may be versioned, and unknown visibility stays local. Explicit public neutral templates are a separate distribution choice. Creation does not authorize staging or publication.
- Prefer built-in agents. A custom role needs a durable difference in ownership, permissions, tools or output. Leave model/reasoning unset until a supported environment and stable need justify an override.
- Put task-routing procedures in conditional guides. Templates do not authorize delegation, separate tasks, dependencies or installation.

For project lifecycle, role ownership or shared mutable resources, read [project environment routing](project-environment-routing.md). Adapt from actual runtime and acceptance needs; optional roles are not enabled by selecting a template.

Keep capability-selection and data-transfer criteria in applicable global/project guidance; exact tool commands stay with their maintained owner. Choose platform-specific Skills only for the selected platform, SDK or tool. Generic words such as agent, React, environment variables or diagram do not select a provider, framework, hosted service or provisioning workflow. Preserve mandatory tool prerequisites once that tool is selected.

When recording code-maintenance preferences, keep equivalent syntax, return types, explicit-public and responsibility-based member order at their durable layer. Judge extraction/inlining by the complete call chain, meaningful abstraction and navigation cost; avoid pass-through layers without making callers hard to read. Preserve type/file cohesion and one state owner, keep framework-specific Component/Service rules with that framework, and leave concrete refactor candidates as task work unless implementation is authorized. Do not invent fixed length or layer-count limits.
