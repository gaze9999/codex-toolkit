---
name: multilingual-proofreading
description: Proofread Traditional Chinese, English or Japanese prose for terminology, punctuation, spelling, grammar and natural wording, or maintain a requested terminology profile. Use for requested proofreading or material document-quality gaps, not automatic translation or a blanket check on every chat reply.
metadata:
  short-description: Language-aware proofreading and terminology consistency
  version: "0.4.16"
  author: "gaze9999"
  repository: "https://github.com/gaze9999/codex-toolkit"
---

# Multilingual Proofreading

Preserve the author's meaning, factual claims, register and terminology. Infer the target language and audience from the material, use the user's explicit style choices, and ask only when an ambiguity changes the correction.

## Choose the applicable profile

- Traditional Chinese: use Taiwan terminology, preserve the enumeration comma `、` in Chinese lists, and use the requested half-width punctuation elsewhere. Normally connect clauses with commas, use a period only when meaning requires separate sentences, do not use semicolons for segmentation, and omit final periods when that preference applies. Preserve periods inside filenames, versions and decimals.
- For Taiwan Chinese software prose, describe API, tool, module or system integration as `串接`; retain `接線` for physical wiring or mathematical tangents. Consult the available project/setup vocabulary for context-dependent choices, including `設定`, `預設`, `相依套件`, `呼叫`, `建置`, `本機`, `唯讀`, `記錄檔` and `儲存庫`. Keep information/message, user/client and cache/buffer meanings distinct. Manually assess wording that a narrow dictionary pattern does not match; do not replace all occurrences of an ambiguous term.
- For agent instructions and personal tooling, use `工作規範`, `設定管理` or `權限管理` according to meaning instead of a generic governance label. Retain established `AI 治理`, `資料治理`, `公司治理`, formal names and identifiers such as `agent-governance`. Contextual lint advice has no automatic fix; choose the wording from the actual responsibility.
- Authored Taiwan Traditional Chinese progress, handoffs and final reports also need a manual script/terminology review, including returned agent text. Preserve quotes and identifiers. A term list is not a complete simplified-character detector; narrow rules supplement semantic review rather than authorize blanket conversion
- English: use the document's English convention, retain normal sentence punctuation, and distinguish spelling, grammar and semantic editing. Add verified product names to the applicable dictionary rather than suppressing all unknown words.
- Japanese: preserve `、。`, keep `ですます` or `である` consistent within the intended register, and do not apply Chinese terminology or punctuation substitutions.
- For mixed-language documents, check separately by language segment or the author's declared file profile. Preserve quoted source text, code, URLs, identifiers, names and citations; distinguish corrections to surrounding prose from changes to literal material. Do not infer language from a filename alone when it conflicts with the actual content.

## Check and correct

For requested Taiwan Chinese vocabulary/rule maintenance, read [Taiwan terminology sources](references/taiwan-terminology.md). Keep official terminology, product/project wording and personal preferences distinguishable; ordinary proofreading does not require collecting new entries.

Select actually available terminology, punctuation, spelling or grammar capabilities by the languages, local rules and approved data boundary. Use the current project configuration when applicable. Reuse a compatible CLI or MCP, inspect its schema or help, and use an available setup Skill only if installation or diagnosis is needed. Tool recipes and versions belong in the setup catalog, not this workflow.

For reproducible file or batch checks, prefer an existing compatible local CLI with the project's language configuration. Keep an available MCP when its typed lint/fix results or client access better fit the task. Inspect write semantics: a CLI fix option may rewrite files, while a server may return corrected text for review. Interface choice does not change the approved processing location or authorize rule installation.

For document creation or revision, run available textlint or an equivalent language/terminology checker on authored or changed prose before delivery, then manually review Taiwan terminology and meaning. If no compatible checker is available or the check fails, notify the user with the unchecked scope and perform the available manual review. Sensitive text may skip tool processing and temporary lint files; keep the manual terminology review and report the exception. Assess each finding in context, then review meaning, naturalness, logical consistency and unsupported factual changes. A dictionary match or clean lint result does not establish complete grammar or factual accuracy. Apply only clear in-scope corrections, rerun affected checks, and retain unresolved context-dependent wording as a concrete question or note.

Before applying terminology or punctuation fixes, identify specification-defined UI titles, field labels, buttons, statuses and messages. Preserve their exact text, including HTML element content and punctuation, unless the user/task explicitly authorizes a copy change. A lint finding is not change authorization. Use an available HTML/literal-text protection filter, a project-owned list of exact protected strings, inline code/blockquotes in lint input, or checks restricted to surrounding authored prose. Do not alter authoritative sources to satisfy a dictionary. A checker cannot infer specification ownership from plain text; manually compare proposed fixes with the source and approved scope.

Respect the selected tool's write behavior. A corrected-content result is a proposed replacement until written to the authorized target; preserve concurrent changes and do not blindly apply fixes to quotations or code. Keep company and private text in the approved processing environment, including any grammar service.

Deliver the corrected text or requested file, explain only consequential changes or ambiguities, and distinguish actual automated checks from semantic review. Do not turn a proofreading request into translation, publishing, rule installation or a new terminology policy.
