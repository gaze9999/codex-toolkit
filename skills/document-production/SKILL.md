---
name: document-production
description: Create requested downloadable PDF, DOCX or Markdown artifacts from supplied content and sources. Use for finished document delivery, not chat-only drafts, source extraction or repository README/license maintenance.
metadata:
  short-description: Default-PDF document production pipeline with DOCX and Markdown support
  version: "0.4.14"
  author: "gaze9999"
  repository: "https://github.com/gaze9999/codex-toolkit"
---

# Document Production

Turn user content, sources, and constraints into deliverable documents rather than drafts or generation prompts. Default to PDF; honor explicit DOCX, Markdown, or multi-format requests.
Activate only when the user explicitly requests a finished downloadable artifact. For chat-only drafting, summaries, translation, or planning, use the corresponding workflow instead.

## Core workflow

- Derive the goal, audience, existing material, required sources, and constraints from the request before building the information architecture; ask only for gaps that materially affect the artifact.
- When external information is required, use reliable sources that directly support the claim and verify time-sensitive facts first.
- Create an actual openable artifact at the requested or authorized destination. Inspect an existing target before replacing it and preserve independent changes. Preserve user-supplied facts, figures, terminology, and citations; do not invent unsupported information.
- Choose available document, spreadsheet, chart or conversion capabilities by the requested format, editability, layout and data boundary. Follow the selected capability's own instructions, verify its actual output and formula-calculation support, and use local processing when data cannot leave the approved environment. Use relevant format guidance only when needed. For standalone LaTeX, prefer an available built-in editor and compiler, retain the same source for follow-up edits, and distinguish compilation from visual QA.
- Read [Document Production Guidelines](references/document-production-guidelines.md) when format-specific or layout guidance is needed.

## Format and quality

- PDF: preserve selectable text and correct Traditional Chinese or Japanese rendering; inspect contents, headings, tables, and whitespace when rendering is available.
- DOCX: use native Heading, TOC, and page-number fields; render when needed to confirm pagination and contents.
- Markdown: keep a continuous heading hierarchy and do not simulate pagination or fixed paper layout.
- Across formats, keep facts, sections, and citations consistent while allowing format-specific layout differences.
- Check authored prose with available textlint or an equivalent language checker, then review meaning and Taiwan terminology manually. Preserve source quotes, legal text, code, identifiers and English/Japanese conventions. Check PDF/DOCX source prose before rendering. Report unavailable, failed or unchecked coverage. Sensitive content may skip tool processing and temporary files; review it manually and report the exception.

For scientific, medical, health, pharmaceutical, or psychological content, use APA 7 in-text citations and references. All other factual claims also require traceable sources that directly support them.

For teaching order, purpose-specific outline references, examples/images and explanation-first wording, read [document presentation](references/presentation.md) only when that aspect is in scope. Preserve an effective existing structure during maintenance, patch the affected content/references and avoid broad rewrites or document moves without authorized need. Keep authoritative wording, legal notices, side effects, data boundaries and material verification limits.

## On-demand verification

When a compatible Python runtime is available, resolve and run the matching validator relative to this Skill: `scripts/validate_pdf.py`, `scripts/validate_docx.py`, `scripts/validate_markdown.py`, or `scripts/validate_apa7.py`. Otherwise use equivalent available inspection and report the bundled validator as not run. Install optional tooling only with user authorization. When rendering or another check cannot be completed, mark it unverified with the reason rather than claiming success.

In the final response, list only deliverable links, formats, completed checks, and unverified items.
