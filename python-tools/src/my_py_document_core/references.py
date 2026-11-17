"""Bounded, read-only Markdown link and reverse-reference analysis."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import unquote

_LINK = re.compile(r"""(!?)\[([^\]]*)\]\(([^)\s]+)(?:\s+(?:"[^"]*"|'[^']*'))?\s*\)""")
_HEADING = re.compile(r"^ {0,3}(#{1,6})\s+(.+?)\s*#*\s*$")
_FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})")
_INLINE_CODE = re.compile(r"(`+)(.*?)\1")
_MAX_DOCUMENTS = 500
_MAX_AFFECTED = 5_000
_MAX_FILE_BYTES = 1_048_576
_MAX_TOTAL_BYTES = 16 * _MAX_FILE_BYTES
_MAX_REFERENCES = 10_000


@dataclass(frozen=True)
class Reference:
    source: str
    line: int
    target: str
    anchor: str | None
    exists: bool | None
    kind: str = "link"
    reason: str | None = None
    resolved_target: str | None = None


def slugify(text: str) -> str:
    """GitHub-style heading slug: lowercase, remove punctuation, spaces to hyphens."""
    value = text.lower()
    value = re.sub(r"[^\w\-\s]", "", value, flags=re.UNICODE)
    return re.sub(r"\s+", "-", value.strip())


def _mask_code(line: str) -> str:
    return _INLINE_CODE.sub(lambda match: " " * len(match.group(0)), line)


def _lines(text: str):
    fence = None
    for number, raw in enumerate(text.splitlines(), 1):
        marker = _FENCE.match(raw)
        if marker:
            token = marker.group(1)
            if fence is None:
                fence = token
                continue
            if token.startswith(fence) and not raw[marker.end():].strip():
                fence = None
                continue
        if fence is None:
            yield number, raw


def analyze_references(root: str | Path, documents: list[str | Path], affected_paths: list[str | Path] | None = None) -> dict:
    """Resolve supported local Markdown links among explicitly selected documents.

    Only ATX headings and inline links/images are parsed. Reference-style links,
    raw HTML, multiline link syntax and nested-parenthesis destinations are not supported.
    """
    base = Path(root).resolve(strict=True)
    if not base.is_dir() or len(documents) > _MAX_DOCUMENTS or len(affected_paths or []) > _MAX_AFFECTED:
        raise ValueError("expected a directory and at most 500 documents and 5000 affected paths")
    diagnostics = []
    headings: dict[str, set[str]] = {}
    links: list[tuple[str, int, str, str]] = []
    budget = _MAX_TOTAL_BYTES
    truncated = False
    for item in documents:
        path = (base / item).resolve()
        if not path.is_relative_to(base):
            raise ValueError(f"document escapes root: {item}")
        rel = path.relative_to(base).as_posix()
        if rel in headings:
            continue
        try:
            if not path.is_file() or path.suffix.lower() not in {".md", ".markdown", ".mdx"}:
                raise ValueError("expected a readable Markdown file")
            limit = min(_MAX_FILE_BYTES, budget)
            with path.open("rb") as stream:
                raw = stream.read(limit + 1)
            budget -= len(raw)
            if len(raw) > limit:
                raise ValueError("document exceeds the remaining size limit")
            text = raw.decode("utf-8-sig")
        except (OSError, ValueError) as error:
            diagnostics.append({"path": rel, "reason": str(error)})
            if budget <= 0:
                truncated = True
                break
            continue
        names: set[str] = set()
        counts: dict[str, int] = {}
        for number, raw_line in _lines(text):
            heading = _HEADING.match(raw_line)
            if heading:
                slug = slugify(_INLINE_CODE.sub(r"\2", heading.group(2)))
                count = counts.get(slug, 0)
                while (slug if count == 0 else f"{slug}-{count}") in names:
                    count += 1
                names.add(slug if count == 0 else f"{slug}-{count}")
                counts[slug] = count + 1
            for match in _LINK.finditer(_mask_code(raw_line)):
                destination = match.group(3)
                if not destination:
                    continue
                if re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", destination) or destination.startswith("//"):
                    continue
                if len(links) >= _MAX_REFERENCES:
                    truncated = True
                    continue
                links.append((rel, number, destination, "image" if match.group(1) else "link"))
        headings[rel] = names
    affected = set()
    for item in affected_paths or []:
        target = (base / item).resolve()
        if not target.is_relative_to(base):
            raise ValueError(f"affected path escapes root: {item}")
        affected.add(target.relative_to(base).as_posix())
    references = [asdict(_resolve(base, headings, *row)) for row in links]
    reverse = [row for row in references if row["resolved_target"] is not None
               and (not affected or row["resolved_target"] in affected)]
    return {"root": str(base), "documents": sorted(headings), "references": references,
            "reverse_references": reverse, "diagnostics": diagnostics, "partial": bool(diagnostics) or truncated,
            "truncated": truncated, "unsupported": ["reference-style links", "raw HTML links", "multiline link syntax",
            "nested-parenthesis destinations", "setext headings"]}


def _resolve(base, headings, source, line, destination, kind):
    name, _, anchor = destination.partition("#")
    document = base / source
    try:
        target = (document.parent / unquote(name)).resolve() if name else document
        key = target.relative_to(base).as_posix()
    except (ValueError, OSError, RuntimeError):
        return Reference(source, line, destination, anchor or None, False, kind, "outside-or-invalid-path")
    if not target.exists():
        exists, reason = False, "missing-file"
    elif not anchor:
        exists, reason = True, None
    elif key not in headings:
        exists, reason = None, "anchor-not-inspected"
    else:
        exists = _normalize_anchor(anchor) in headings[key]
        reason = None if exists else "missing-anchor"
    return Reference(source, line, destination, anchor or None, exists, kind, reason, key)


def _normalize_anchor(anchor: str) -> str:
    """Decode URL escapes and normalize a heading fragment for comparison."""
    return unquote(anchor).strip().lower().replace(" ", "-")
