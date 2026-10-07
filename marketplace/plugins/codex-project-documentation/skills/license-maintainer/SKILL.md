---
name: license-maintainer
description: Maintain repository LICENSE, NOTICE, COPYRIGHT, SPDX and README license references from verified ownership and distribution evidence. Use for licensing files, not general README writing; never choose or change a license without explicit direction.
metadata:
  version: "0.4.13"
  author: "gaze9999"
  repository: "https://github.com/gaze9999/codex-toolkit"
---

# License Maintainer

Maintain copyright and licensing documents without inventing ownership, legal terms, permissions, or compatibility conclusions.

## Activation and boundary

- Use when the user asks to create, audit, correct, or synchronize `LICENSE`, `LICENSES/`, `NOTICE`, `COPYRIGHT`, third-party notices, SPDX identifiers, source headers, package metadata, or a README license section. An audit is read-only unless edits are authorized.
- Use `readme-maintainer` for general README restructuring; use this Skill for the licensing facts and exact legal-document changes.
- Treat license selection, relicensing, contributor consent, dual-licensing, copyright ownership, and legal compatibility as user or qualified legal decisions. Ask for the missing decision instead of choosing one.
- Do not remove existing notices, attribution, exceptions, trademarks, or contributor ownership merely to standardize formatting.

## Establish evidence

- Start with applicable instructions and the existing license/notice files for the requested paths. Read relevant README sections, manifests, lockfiles, headers, contribution policy, ownership history or release artifacts only when needed to resolve ownership, attribution or distribution scope.
- Identify whether the repository is source-available, open source, proprietary, dual-licensed, generated from another project, or missing enough evidence to decide.
- Confirm the exact license name, version, `-only` versus `-or-later` choice, copyright holder text, year or year range, exceptions, and covered paths from explicit project evidence or the user. Preserve the meaning of SPDX `AND`, `OR`, `WITH` and parentheses; do not replace a compound expression with a single license or infer consent from its syntax.
- Obtain standard license text and SPDX identifiers from authoritative current sources when exact wording matters. Preserve verbatim legal text; do not paraphrase a standard license body.
- Separate first-party licensing from third-party attribution. A dependency's license does not automatically determine the repository license.

## Apply the narrow change

- Preserve required legal clauses verbatim.
- Prefer conventional filenames and preserve the repository's established line endings, encoding, header style, package metadata format, and language.
- Keep the canonical legal text in its dedicated file. README content should usually provide a short factual summary and a relative link rather than duplicate the full license.
- Update package metadata, SPDX headers, notice indexes, generated notice inputs, and README references only when they are in scope and supported by the same verified decision.
- For generated third-party notices, use the project's existing generator and lockfile when available; do not manually guess the shipped dependency set.
- Never insert personal addresses, private company information, credentials, or unverified contributor names.

## Verify and report

- Check authored explanations with available textlint or an equivalent language checker, then review meaning and Taiwan terminology manually. Preserve canonical licenses, notices, source quotes, code, identifiers and English/Japanese conventions. Report unavailable, failed or unchecked coverage. Sensitive content may skip tool processing and temporary files; review it manually and report the exception.

- Check filenames, internal links, SPDX syntax, manifest values, covered paths, holder names, year text, required notices, and packaging inclusion against repository state.
- Use an existing license or notice validator when the project already provides one. Do not claim legal compatibility from syntax validation alone.
- Report the evidence used, files changed, exact user-provided decisions, validation performed, and any unresolved ownership, compatibility, distribution, or attribution question.
