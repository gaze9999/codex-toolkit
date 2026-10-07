---
name: document-source-matching
description: Find and assess existing Markdown extracts by recorded original-source path and SHA-256. Use for read-only source matching, not conversion, rewriting or semantic specification decisions.
metadata:
  short-description: Match Markdown extracts to original sources
  version: "0.4.14"
  author: "gaze9999"
  repository: "https://github.com/gaze9999/codex-toolkit"
---

# Document Source Matching

Choose an available local document-indexing or path/metadata capability that can retrieve bounded candidates by recorded source path or SHA-256 within the identified scope. An existing CLI or native file/hash inspection is sufficient for bounded lookups; use a compatible MCP when repeated structured queries or the client's access model justify it. Verify its actual options/schema and read permissions, keep private source material local, and report matching limits when metadata or hashes are unavailable. Do not install or reconfigure tools during ordinary lookup

- Treat `current` as metadata and hash agreement, `stale` as the same recorded path with different content, and `candidate` as a weaker filename-only or incomplete metadata match. Hash agreement does not prove extraction completeness, correct OCR/tables or semantic accuracy
- Preserve each candidate's path, recorded source, hash, extraction time and match reasons; do not choose by filename alone when a hash is available
- For multiple versions, distinguish original revision time from file modification, download and extraction times. Present a timeline from verified revisions when available, preserve timezone and precision, and label unknown times. Hashes establish identity/freshness, not chronological or semantic authority; do not choose a governing specification by time alone
- Original PDF, Office file or other source remains authoritative. Start from relevant extract sections; reopen only needed original sections for visual evidence, missing/unclear content, stale or conflicting versions, or an explicit original-source check. Validation rules do not by themselves require routine original rereading when the extract is usable; label extract-only evidence separately from inspected originals
- Lookup is read-only. Do not regenerate, overwrite, synchronize or delete a Markdown file without separate authorization
