# Document teaching and outline references

Read when the requested document needs a teaching sequence, reusable outline, example or visual. Select by the audience and intended decision/use, not the output extension.

| Document purpose | Adaptable outline |
|---|---|
| First-use tutorial | Goal and prerequisites → small example → steps to one useful result → expected output/check → linked next task |
| Operational how-to | Situation and required access → exact bounded operation → observable outcome → recovery/troubleshooting where needed |
| API/tool reference | Purpose and version → inputs/options → outputs/errors/exit codes → representative example → compatibility/source |
| Specification | Scope and source authority → confirmed behavior/data → necessary tables/examples → unresolved decisions/IDs → verification criteria |
| Analysis or report | Result/decision → supporting evidence → relevant comparison → limits affecting interpretation → concrete next action |

These are references, not mandatory templates. Omit irrelevant sections, preserve established headings/IDs and choose the ordering that answers the reader's first question. Important decisions and operating constraints may precede a table; detailed explanation/examples may follow it. Do not add a fixed section count, full command catalog or generic disclaimer.

Keep user-provided facts, required terminology, citations and authoritative specification wording. Explain dependencies, data boundaries, side effects and verification limits where they change the reader's decision or operation. Put pending execution checks in the existing work record and relevant handoff. Remove defensive comparisons, broad liability prose and repeated maintenance/synchronization narration that do not serve the document's purpose; legal notices remain under their own authority.

Examples should show the smallest safe input, operation and expected result. Use actual verified outputs or clearly labeled illustrative examples, never invented execution evidence. Screenshots/diagrams are optional: use them when a UI operation, layout, result or relation needs a visual, include useful alt text/captions and protect credentials, private data and paths. Check current version/state and the actual rendered deliverable when layout matters.

For maintenance, retain the effective existing structure and patch only affected content and live references. Do not substantially rewrite, rename/move documents, change specifications or regenerate images merely to conform to these outlines. An explicitly requested redesign may restructure within its stated scope. New document creation follows the requested purpose; an update workflow does not become authoring permission automatically.

Keep lengthy instructions and format-specific procedures in the existing relevant references. English internal guidance may contain localized output examples; user-visible content follows the requested language. Source, language, link, rendering and actual operation checks are distinct evidence.

## Charts and diagrams

Keep the document's question, narrative and governing sources with its owner. Use the independently callable [data-visualization Skill](../../data-visualization/SKILL.md) when a chart, diagram or interactive explanation helps the reader compare, explore or understand relationships. It handles visual selection, data mapping, rendering and export checks. Reference one maintained figure source from the document and include a useful caption, units, filters and source revision. Frontend visuals cover interaction, request/state behavior and maintainability.

## Reading experience

Design for the actual reading surface and task: clear semantic headings/navigation, important results before secondary detail, readable line lengths/tables, nearby explanations and copyable examples. Avoid image-only instructions, unexplained abbreviations, unnecessary nesting and hiding required actions in collapsible content. Use meaningful link text and alt text, and preserve text selection and accessible heading order where the format supports them.

Markdown/web/mobile readers need tables and code examples that remain usable in a narrow view. PDF/DOCX readers also need stable pagination, repeated table headers where appropriate, legible typography and consistent spacing. Verify the relevant rendered result when changing layout; source checks alone do not prove readability/accessibility. Do not build a new UI or reformat unrelated documents merely to apply these principles.
