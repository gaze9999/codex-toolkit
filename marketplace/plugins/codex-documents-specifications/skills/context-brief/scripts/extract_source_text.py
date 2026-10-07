#!/usr/bin/env python3
"""Extract readable text from common source-document formats.

This helper is intentionally dependency-light. It uses the Python standard library
for DOCX / XLSX / CSV / TXT / MD / JSON and optional local tools or packages for
PDF extraction when available.

Supported inputs:
- .txt, .md, .markdown, .json, .yaml, .yml, .csv
- .docx through OOXML ZIP parsing
- .xlsx through OOXML ZIP parsing
- .pdf through pypdf, pdfplumber, PyPDF2, or pdftotext when available

The output is meant to be a compact extraction base for a Codex context brief,
not a final source of truth. Always preserve uncertainty when extraction is
partial, lossy, or unavailable.
"""

from __future__ import annotations

import argparse
import csv
import html
import json
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Iterable

from ocr_fallback import ocr_fallback
from xml.etree import ElementTree as ET

TEXT_EXTENSIONS = {".txt", ".md", ".markdown", ".yaml", ".yml", ".json"}
SPREADSHEET_EXTENSIONS = {".xlsx"}
DOCX_EXTENSIONS = {".docx"}
PDF_EXTENSIONS = {".pdf"}
CSV_EXTENSIONS = {".csv", ".tsv"}
OCR_EXTENSIONS = PDF_EXTENSIONS | DOCX_EXTENSIONS | SPREADSHEET_EXTENSIONS | {".pptx"} | {
    ".bmp", ".gif", ".jpeg", ".jpg", ".png", ".tif", ".tiff", ".webp"
}

XML_NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
}


def normalize_ws(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def read_text(path: Path) -> str:
    raw = path.read_bytes()
    for encoding in ("utf-8", "utf-8-sig", "cp950", "big5", "shift_jis", "latin-1"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def extract_text_file(path: Path) -> str:
    text = read_text(path)
    if path.suffix.lower() == ".json":
        try:
            parsed = json.loads(text)
            return json.dumps(parsed, ensure_ascii=False, indent=2)
        except json.JSONDecodeError:
            return text
    return text


def extract_csv(path: Path) -> str:
    delimiter = "\t" if path.suffix.lower() == ".tsv" else ","
    text = read_text(path)
    rows: list[list[str]] = []
    reader = csv.reader(text.splitlines(), delimiter=delimiter)
    for row in reader:
        rows.append([cell.strip() for cell in row])
    if not rows:
        return ""
    lines = []
    for index, row in enumerate(rows, start=1):
        line = " | ".join(cell for cell in row if cell)
        if line:
            lines.append(f"row {index}: {line}")
    return "\n".join(lines)


def xml_text(element: ET.Element) -> str:
    chunks: list[str] = []
    for node in element.iter():
        tag = node.tag.rsplit("}", 1)[-1]
        if tag in {"t", "instrText"} and node.text:
            chunks.append(node.text)
        elif tag in {"tab"}:
            chunks.append("\t")
        elif tag in {"br", "cr"}:
            chunks.append("\n")
    return "".join(chunks)


def extract_docx(path: Path) -> str:
    paragraphs: list[str] = []
    with zipfile.ZipFile(path) as zf:
        names = set(zf.namelist())
        targets = ["word/document.xml"]
        targets += sorted(name for name in names if name.startswith("word/header") and name.endswith(".xml"))
        targets += sorted(name for name in names if name.startswith("word/footer") and name.endswith(".xml"))
        targets += sorted(name for name in names if name.startswith("word/footnotes") and name.endswith(".xml"))
        targets += sorted(name for name in names if name.startswith("word/endnotes") and name.endswith(".xml"))

        for target in targets:
            if target not in names:
                continue
            root = ET.fromstring(zf.read(target))
            paragraphs.append(f"\n## {target}\n")
            for para in root.findall(".//w:p", XML_NS):
                text = normalize_ws(xml_text(para))
                if text:
                    paragraphs.append(text)
            for table in root.findall(".//w:tbl", XML_NS):
                for row in table.findall(".//w:tr", XML_NS):
                    cells = []
                    for cell in row.findall(".//w:tc", XML_NS):
                        value = normalize_ws(xml_text(cell))
                        if value:
                            cells.append(value)
                    if cells:
                        paragraphs.append(" | ".join(cells))
    return "\n".join(paragraphs)


def read_xlsx_shared_strings(zf: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in zf.namelist():
        return []
    root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
    strings: list[str] = []
    for item in root.findall(".//s:si", XML_NS):
        parts = []
        for text_node in item.findall(".//s:t", XML_NS):
            if text_node.text:
                parts.append(text_node.text)
        strings.append("".join(parts))
    return strings


def extract_xlsx(path: Path, max_rows_per_sheet: int) -> str:
    lines: list[str] = []
    with zipfile.ZipFile(path) as zf:
        names = set(zf.namelist())
        shared = read_xlsx_shared_strings(zf)
        sheet_names = sorted(name for name in names if re.match(r"xl/worksheets/sheet\d+\.xml$", name))
        for sheet in sheet_names:
            root = ET.fromstring(zf.read(sheet))
            lines.append(f"\n## {sheet}\n")
            rows = root.findall(".//s:sheetData/s:row", XML_NS)
            for row_index, row in enumerate(rows, start=1):
                if row_index > max_rows_per_sheet:
                    lines.append(f"[TRUNCATED] More than {max_rows_per_sheet} rows in this sheet.")
                    break
                cells = []
                for cell in row.findall("s:c", XML_NS):
                    ref = cell.attrib.get("r", "")
                    cell_type = cell.attrib.get("t")
                    value_node = cell.find("s:v", XML_NS)
                    inline_text_node = cell.find(".//s:is/s:t", XML_NS)
                    value = ""
                    if cell_type == "s" and value_node is not None and value_node.text:
                        try:
                            value = shared[int(value_node.text)]
                        except (ValueError, IndexError):
                            value = value_node.text
                    elif inline_text_node is not None and inline_text_node.text:
                        value = inline_text_node.text
                    elif value_node is not None and value_node.text:
                        value = value_node.text
                    value = normalize_ws(html.unescape(value))
                    if value:
                        label = ref or "cell"
                        cells.append(f"{label}={value}")
                if cells:
                    lines.append("; ".join(cells))
    return "\n".join(lines)


def extract_pdf_with_python(path: Path) -> str | None:
    candidates = ["pypdf", "PyPDF2"]
    for module_name in candidates:
        try:
            module = __import__(module_name)
        except Exception:
            continue
        try:
            reader_cls = getattr(module, "PdfReader")
            reader = reader_cls(str(path))
            chunks = []
            for index, page in enumerate(reader.pages, start=1):
                page_text = page.extract_text() or ""
                if page_text.strip():
                    chunks.append(f"\n## PDF page {index}\n{page_text}")
            return "\n".join(chunks)
        except Exception:
            continue
    return None


def extract_pdf_with_pdfplumber(path: Path) -> str | None:
    try:
        import pdfplumber
    except ImportError:
        return None
    try:
        with pdfplumber.open(str(path)) as pdf:
            chunks = []
            for index, page in enumerate(pdf.pages, start=1):
                page_text = page.extract_text() or ""
                if page_text.strip():
                    chunks.append(f"\n## PDF page {index}\n{page_text}")
            return "\n".join(chunks) or None
    except Exception:
        return None


def extract_pdf_with_cli(path: Path) -> str | None:
    pdftotext = shutil.which("pdftotext")
    if pdftotext:
        try:
            result = subprocess.run(
                [pdftotext, "-layout", str(path), "-"],
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=60,
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout
            if result.stderr.strip():
                return f"[pdftotext failed: {result.stderr.strip()}]"
        except Exception as exc:
            return f"[pdftotext execution failed: {exc}]"
    return None


def extract_pdf(path: Path) -> str:
    text = extract_pdf_with_python(path)
    if text and text.strip():
        return text
    text = extract_pdf_with_pdfplumber(path)
    if text and text.strip():
        return text
    text = extract_pdf_with_cli(path)
    if text is not None:
        return text
    return "[PDF text extraction unavailable: no compatible PDF extractor was found. Treat source coverage as unverified.]"


def extract(path: Path, max_rows_per_sheet: int) -> tuple[str, str]:
    suffix = path.suffix.lower()
    if suffix in TEXT_EXTENSIONS:
        return "text", extract_text_file(path)
    if suffix in CSV_EXTENSIONS:
        return "csv", extract_csv(path)
    if suffix in DOCX_EXTENSIONS:
        return "docx", extract_docx(path)
    if suffix in SPREADSHEET_EXTENSIONS:
        return "xlsx", extract_xlsx(path, max_rows_per_sheet)
    if suffix in PDF_EXTENSIONS:
        return "pdf", extract_pdf(path)
    return "unsupported", f"[Unsupported file type: {suffix or 'no extension'}]"


def truncate(text: str, max_chars: int) -> tuple[str, bool]:
    if max_chars <= 0 or len(text) <= max_chars:
        return text, False
    return text[:max_chars].rstrip() + "\n\n[TRUNCATED] Extraction exceeded max character limit.", True


def render_ocr_records(records: list[dict[str, object]]) -> str:
    lines = ["", "## OCR-derived text", "", "- Source coverage: partial; verify OCR-derived contracts against the original visual source.", ""]
    for record in records:
        confidence = record["confidence"] if record["confidence"] is not None else "unavailable"
        lines.extend([f"### {record['location']}", f"- OCR confidence: {confidence}", str(record["text"]) or "[No text recognized]", ""])
    return "\n".join(lines)


def native_extraction_insufficient(path: Path, body: str) -> bool:
    if path.suffix.lower() not in OCR_EXTENSIONS:
        return False
    useful = re.sub(r"\[[^\]]+\]|\W+", "", body, flags=re.UNICODE)
    return body.lstrip().startswith("[") or len(useful) < 80


def build_output(path: Path, source_type: str, body: str, truncated: bool, ocr_status: str) -> str:
    neutral_ocr = {"not_requested", "not_applicable", "skipped_native_text_sufficient"}
    status = "partial" if truncated or body.startswith("[") or ocr_status not in neutral_ocr else "extracted"
    header = [
        f"# Extracted Source Text: {path.name}",
        "",
        "## Extraction metadata",
        f"- Source path: {path}",
        f"- Source type: {source_type}",
        f"- Extraction status: {status}",
        f"- OCR fallback: {ocr_status}",
        "- Intended use: Build a reusable Codex context brief; verify important contracts against the original source when possible.",
        "",
        "## Extracted text",
        "",
    ]
    return "\n".join(header) + body.strip() + "\n"


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Extract text from source documents for Codex context brief creation.")
    parser.add_argument("source", help="Source file path: PDF, DOCX, XLSX, CSV, TXT, MD, JSON, YAML.")
    parser.add_argument("--out", help="Optional output .md/.txt path. Defaults to stdout.")
    parser.add_argument("--max-chars", type=int, default=80000, help="Maximum extracted characters to print/write. Use 0 for no limit.")
    parser.add_argument("--max-rows-per-sheet", type=int, default=200, help="Maximum rows per XLSX worksheet.")
    parser.add_argument("--ocr-fallback", action="store_true", help="Optionally OCR bounded PDF pages or embedded OOXML images when native extraction is insufficient.")
    parser.add_argument("--force-ocr", action="store_true", help="OCR eligible visual content even when native text looks sufficient.")
    parser.add_argument("--ocr-max-items", type=int, default=20, help="Maximum PDF pages or embedded images to OCR (1-100). Default: 20.")
    parser.add_argument("--ocr-lang", default="eng", help="Installed Tesseract language code. Default: eng.")
    args = parser.parse_args(list(argv) if argv is not None else None)

    path = Path(args.source).expanduser().resolve()
    if not path.exists() or not path.is_file():
        print(f"FAIL source_not_found: {path}", file=sys.stderr)
        return 1

    try:
        source_type, extracted = extract(path, args.max_rows_per_sheet)
        ocr_status = "not_requested"
        if args.ocr_fallback and (args.force_ocr or native_extraction_insufficient(path, extracted)):
            records, ocr_status = ocr_fallback(path, args.ocr_max_items, args.ocr_lang)
            if records:
                extracted += render_ocr_records(records)
        elif args.ocr_fallback:
            ocr_status = "skipped_native_text_sufficient" if path.suffix.lower() in OCR_EXTENSIONS else "not_applicable"
        extracted = normalize_ws(extracted)
        extracted, truncated = truncate(extracted, args.max_chars)
        output = build_output(path, source_type, extracted, truncated, ocr_status)
    except zipfile.BadZipFile:
        print("FAIL invalid_zip_container: file is not a valid DOCX/XLSX ZIP container", file=sys.stderr)
        return 1
    except ET.ParseError as exc:
        print(f"FAIL xml_parse_error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # Keep script output concise for agent use.
        print(f"FAIL extraction_error: {exc}", file=sys.stderr)
        return 1

    if args.out:
        out_path = Path(args.out).expanduser().resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(output, encoding="utf-8")
        print(f"PASS extracted: {path.name} -> {out_path}")
    else:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
