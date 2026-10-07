---
name: context-brief
description: Turn explicitly supplied implementation specifications into reusable Codex Markdown context briefs. Use for implementation context, not ordinary summaries, document conversion, task guides or current-progress handoffs.
metadata:
  short-description: Create concise, traceable coding context briefs
  version: "0.4.13"
  author: "gaze9999"
  repository: "https://github.com/gaze9999/codex-toolkit"
---

# Context Brief

Compress specifications, API documentation, schemas, integration guides, or acceptance criteria into reusable Markdown context briefs for later implementation. Preserve exact contracts and source traceability; do not create ordinary summaries, formal document artifacts, or implementation changes.

## Activation

Use only when all conditions hold:

- The user provides or explicitly identifies readable source material.
- The material contains implementation-relevant contracts, such as behavior, fields, workflows, permissions, error handling, or acceptance criteria.
- The user wants a reusable Codex or coding-agent Markdown context brief.

Use the appropriate workflow instead for generic document conversion, ordinary summaries, Notion organization, formal PDF/DOCX output, a single coding prompt, or post-implementation documentation updates.

## When to create or refresh one

- Do not create a Context Brief after a fixed number of messages or conversation compactions. Compaction supports continuing long-running work and is not itself evidence that a new artifact or conversation is needed.
- Create one when identified implementation-contract material will be reused across separate tasks or conversations, when repeatedly rereading a large governing source is costly, or when a future implementation needs a compact self-contained contract reference.
- Refresh one only when its governing contract, accepted decision, source coverage, or intended implementation scope materially changes.
- Use a task handoff for current progress, changed files, check results, blockers, and the next step. Do not turn chat history, tool logs, or a compaction recap into a Context Brief.
- Keep the same conversation for the same outcome while retained state remains reliable. A distinct deliverable, repository, branch, or independent workstream is a better reason to start a new conversation than compaction count.

## Workflow

- Resolve source boundaries, intended use, and deliverable from the request and available material. Ask only when a gap affects correctness or coverage.
- Locate an existing Markdown extraction from the task and available source/version metadata or pointers, without requiring fixed filenames, same-stem names or a fixed folder; start from its relevant sections. Preserve its original-source identity, locations and coverage; consult only necessary screenshots or original sections for visual evidence, missing/unclear/stale extraction, conflicts, or an explicit original-source check. A usable extraction does not require routine original-file rereading or regeneration.
- Preserve names, paths, fields, enums, status codes, validation, security and permissions, errors, constraints, examples, and acceptance criteria.
- Compress marketing copy, repeated background, and implementation-irrelevant narrative. Do not turn gaps, conflicts, OCR text, historical progress, or current implementation behavior into confirmed contracts. Treat them as evidence unless a governing source or explicit user decision establishes the contract.
- Retaining secrets, credentials, private tokens, or unnecessary personal data requires an explicit user request and implementation need. Preserve only the minimum source detail required for implementation.
- Preserve source boundaries across multiple inputs. For large material, extract only task-relevant sections.
- Check authored prose with available textlint or an equivalent language checker, then review meaning and Taiwan terminology manually. Preserve source quotes, legal text, code, identifiers and English/Japanese conventions. Report unavailable, failed or unchecked coverage. Sensitive content may skip tool processing and temporary files; review it manually and report the exception.

## On-demand tools

- When no usable Markdown extraction exists or a conditional source check is needed, read the relevant original sections. For PDF, DOCX, XLSX, or other structured files, prefer the available native document capability. When a compatible Python runtime is available, the bundled `scripts/extract_source_text.py <source-file>` may be resolved relative to this Skill and used as a compact extraction helper. Use an equivalent available extractor when needed; do not require every environment to install the optional dependencies.
- Use OCR only when native extraction cannot recover scanned content or essential images. If no safe extraction path is available, mark only the affected coverage as unverified rather than blocking independent sections.
- Mark coverage as `partial` or `unverified` when OCR, tables, or extraction are insufficient, and retain source locations.
- Original specifications and confirmed decisions retain authority. Identify evidence read only through an extraction; structural validation does not mean the original was inspected. Do not silently re-extract sources or expand a requested brief refresh into source maintenance.
- When a compatible Python runtime is available, run the Skill-relative `scripts/validate_context_brief.py <brief.md>` after creating the brief; use `--json` when machine-readable output is needed. Otherwise perform equivalent structural checks and report the bundled validator as not run.

## Output contract

When writing is available, honor the requested destination and filename; otherwise use `<source-or-project-name>_Codex_Context_Brief.md` in an authorized workspace location. Include Metadata, Scope, implementation summary, Contracts and invariants, implementation guidance, open items, and source traceability; add API, data-model, workflow, error, or security sections only when applicable.

In the final response, provide the output location, source coverage, completed checks, and material unresolved items.
