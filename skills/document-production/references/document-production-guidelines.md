# Document Production Guidelines

Internal production and QA guidance supplementing `SKILL.md`; this is not a separately installable Skill.

## Content structure

Use the fewest useful sections for the document's purpose. A technical/tutorial document may follow: purpose and scope, prerequisites and concepts, architecture, implementation, examples, failure cases, material limitations, useful templates/checklists and references. Omit irrelevant sections.

- Explain concepts before details; group related practical examples.
- Retain necessary prerequisites without repeating basics for advanced readers.
- Use Mermaid for suitable flows/responsibilities and tables for comparisons. Interactive visuals need a supported delivery format and a real explanatory benefit; simple content stays text.
- Keep heading levels and terminology consistent, remove duplication and follow `SKILL.md`'s Format and quality rules.

## Filenames and versions

- Use a concise, recognizable technical topic name rather than embedding a document version in the filename.
- Formats of the same content share a basename, such as `Coding_Agent_Prompt_Engineering_Tutorial.pdf`, `.docx` and `.md`.
- Record versions only when requested by the user, source or delivery process. Preserve the established format/increment rule rather than inventing Semantic Versioning or a fixed width.
- Omit unconfirmed or irrelevant program versions instead of guessing or adding `unknown` placeholders.

## Contents and navigation

For long or deeply structured documents, use a useful table of contents.

- DOCX: native Heading styles and TOC fields, left-aligned title, right-aligned page numbers with dot leaders/tab stops. `updateFieldsOnOpen=true` requests refresh; verify actual rendered heading/page correspondence.
- PDF: verify displayed TOC pages against final pagination rather than reusing stale DOCX field results.
- Markdown: heading hierarchy is primary navigation; add a TOC only when useful and never invent page numbers.

## Pagination and layout

- Keep headings with at least one following paragraph; avoid stranded headings and widows/orphans.
- Keep tables on one page when they fit. Long tables may span pages with repeated headers and intact rows where possible; prioritize readable widths.
- Keep figures with captions and avoid splitting code/logical blocks unnecessarily. When a block exceeds one page, split reasonably while retaining context.
- Preserve useful whitespace; diagnose large empty areas caused by page breaks, keep-with-next or table settings.

## PDF

PDF is the default when no format was requested. Preserve real text rather than rasterizing full pages, verify all used scripts/symbols and use shareable font handling when feasible.

When rendering is available, inspect actual pages for stranded/cropped headings, TOC pages, split tables, figures/captions, headers/footers, glyphs, overflow, abnormal whitespace and page-number continuity. Without rendering, retain visual QA as unverified; successful generation does not prove layout correctness.

## DOCX

- Use editable native Word structure, Heading styles, TOC and `PAGE` / `NUMPAGES` fields.
- Set `updateFieldsOnOpen=true` when refresh is needed; dynamic fields do not establish final pagination.
- Repeat table headers where needed and avoid excessive whitespace from keep-with-next/keep-together.
- Check headings, TOC, fields, tables and relationships. Render when possible and verify TOC page/heading matches; otherwise report visual QA as unverified.

## Markdown

- Use standard heading hierarchy and appropriate language fences; do not simulate PDF/DOCX pagination.
- Use tables only when the text and columns remain readable; complex content may need sections or lists.
- Keep facts and citations consistent across formats.

## Citations and evidence

- Each source must directly support its claim. Prefer official docs, standards and original technical material for technical claims; original research, systematic reviews, meta-analyses and formal academic sources for research claims.
- Scientific, medical, health, pharmaceutical, psychological and other research-based professional material requires APA 7, including suitable in-text citations and a complete reference list.
- Include available DOIs and verified publication details. Important facts, statistics, experimental/clinical results, risk-benefit conclusions and disputed professional claims need traceable support.
- Do not use mismatched, expired, unverified or purely secondary material as primary evidence. Distinguish facts, inferences, assumptions and unknowns; correlation is not causation and a theoretical mechanism is not proven clinical efficacy.

## Multiple formats and QA status

Create one canonical content source. PDF, DOCX and Markdown retain the same sections, numbers, terminology, sources and conclusions, allowing only format-specific presentation. Check for lost paragraphs/table data, citation drift and inconsistent versions after conversion.

Report checks as passed, failed, not run or unverified according to actual execution and evidence. File creation alone does not establish successful layout QA.

`validate_markdown.py` is a standalone snapshot generated from my-py-tools canonical `markdown/validate_structure.py`; do not hand-edit its algorithm. Preserve the package version and source SHA-256 in its header. Maintainers check it with that repository's `scripts/export_markdown_validator.py --output <snapshot-file> --check`; normal Skill use needs neither that checkout nor a core installation.
