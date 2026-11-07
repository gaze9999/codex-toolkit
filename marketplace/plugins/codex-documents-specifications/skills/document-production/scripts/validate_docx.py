#!/usr/bin/env python3
"""Structural DOCX validator for Document Production.

Uses only Python's standard library. This checks deterministic OOXML structure;
it does not replace visual pagination/render QA in Microsoft Word or a compatible renderer.
"""

from __future__ import annotations

import argparse
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W = f"{{{W_NS}}}"


def result(status: str, check: str, detail: str) -> None:
    print(f"{status}: {check} - {detail}")


def parse_xml(zf: zipfile.ZipFile, name: str) -> ET.Element | None:
    try:
        return ET.fromstring(zf.read(name))
    except KeyError:
        return None
    except ET.ParseError:
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate deterministic DOCX structure.")
    parser.add_argument("file", type=Path)
    args = parser.parse_args()
    path = args.file

    failures = 0
    warnings = 0

    if not path.is_file():
        result("FAIL", "file", "file does not exist")
        return 2

    if path.suffix.lower() != ".docx":
        result("FAIL", "extension", "expected .docx")
        return 2

    if not zipfile.is_zipfile(path):
        result("FAIL", "package", "not a valid ZIP/OOXML package")
        return 2

    with zipfile.ZipFile(path) as zf:
        required = {"[Content_Types].xml", "word/document.xml", "word/styles.xml"}
        missing = sorted(required - set(zf.namelist()))
        if missing:
            failures += 1
            result("FAIL", "required-parts", ", ".join(missing))
        else:
            result("PASS", "required-parts", "core OOXML parts present")

        document = parse_xml(zf, "word/document.xml")
        styles = parse_xml(zf, "word/styles.xml")
        settings = parse_xml(zf, "word/settings.xml")

        if document is None:
            result("FAIL", "document-xml", "cannot parse word/document.xml")
            return 1

        style_ids: set[str] = set()
        if styles is not None:
            for style in styles.findall(f".//{W}style"):
                style_id = style.get(f"{W}styleId")
                if style_id:
                    style_ids.add(style_id)

        heading_paragraphs = 0
        for p in document.findall(f".//{W}p"):
            p_style = p.find(f"./{W}pPr/{W}pStyle")
            if p_style is not None:
                value = p_style.get(f"{W}val", "")
                if value.lower().startswith("heading"):
                    heading_paragraphs += 1

        if heading_paragraphs:
            result("PASS", "headings", f"found {heading_paragraphs} Heading-style paragraphs")
        else:
            warnings += 1
            result("WARN", "headings", "no Heading-style paragraphs found")

        instr_text = " ".join(
            (node.text or "") for node in document.findall(f".//{W}instrText")
        ).upper()

        if "TOC" in instr_text:
            result("PASS", "toc-field", "native TOC field detected")
        else:
            warnings += 1
            result("WARN", "toc-field", "no native TOC field detected")

        has_page = " PAGE " in f" {instr_text} " or instr_text.strip().startswith("PAGE")
        has_numpages = "NUMPAGES" in instr_text
        if has_page or has_numpages:
            result("PASS", "page-fields", f"PAGE={has_page}, NUMPAGES={has_numpages}")
        else:
            warnings += 1
            result("WARN", "page-fields", "PAGE/NUMPAGES fields not detected")

        if settings is not None and settings.find(f".//{W}updateFields") is not None:
            node = settings.find(f".//{W}updateFields")
            value = (node.get(f"{W}val", "true") if node is not None else "true").lower()
            if value not in {"false", "0", "off"}:
                result("PASS", "update-fields", "updateFieldsOnOpen is enabled")
            else:
                warnings += 1
                result("WARN", "update-fields", "updateFields exists but is disabled")
        else:
            warnings += 1
            result("WARN", "update-fields", "updateFieldsOnOpen not detected")

        tables = document.findall(f".//{W}tbl")
        repeat_headers = 0
        for table in tables:
            first_row = table.find(f"./{W}tr")
            if first_row is not None and first_row.find(f"./{W}trPr/{W}tblHeader") is not None:
                repeat_headers += 1

        if tables:
            result(
                "PASS" if repeat_headers == len(tables) else "WARN",
                "table-headers",
                f"{repeat_headers}/{len(tables)} tables have repeat-header on first row",
            )
            if repeat_headers != len(tables):
                warnings += 1
        else:
            result("PASS", "table-headers", "no tables present")

        if style_ids:
            result("PASS", "styles", f"parsed {len(style_ids)} styles")
        else:
            warnings += 1
            result("WARN", "styles", "styles.xml contained no readable style IDs")

    result("INFO", "visual-qa", "render/pagination QA is still required when available")
    print(f"SUMMARY: failures={failures} warnings={warnings}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
