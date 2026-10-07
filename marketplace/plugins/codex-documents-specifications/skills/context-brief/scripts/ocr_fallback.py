"""Optional, bounded OCR fallback for explicit PDF, OOXML, or image inputs.

RapidOCR is preferred because it is a Python package with locally installed ONNX
models. The Tesseract command remains a compatibility fallback when RapidOCR is
not installed or cannot process an input.
"""

from __future__ import annotations

import csv
import io
import re
import shutil
import subprocess
import tempfile
import zipfile
from functools import lru_cache
from pathlib import Path


IMAGE_EXTENSIONS = {".bmp", ".gif", ".jpeg", ".jpg", ".png", ".tif", ".tiff", ".webp"}
OOXML_MEDIA_PREFIXES = {
    ".docx": "word/media/",
    ".xlsx": "xl/media/",
    ".pptx": "ppt/media/",
}


@lru_cache(maxsize=1)
def _rapidocr_engine():
    try:
        from rapidocr import RapidOCR
    except ImportError as exc:
        raise RuntimeError("RapidOCR is not installed.") from exc
    return RapidOCR()


def _ocr_with_rapidocr(image_path: Path) -> tuple[str, float | None]:
    result = _rapidocr_engine()(str(image_path))
    texts = getattr(result, "txts", None) or ()
    scores = getattr(result, "scores", None) or ()
    words = [str(text).strip() for text in texts if str(text).strip()]
    confidences = [float(score) * 100 for score in scores if score is not None]
    return " ".join(words), (sum(confidences) / len(confidences) if confidences else None)


def _ocr_with_tesseract(image_path: Path, language: str) -> tuple[str, float | None]:
    tesseract = shutil.which("tesseract")
    if not tesseract:
        raise RuntimeError("OCR fallback unavailable: no compatible Tesseract executable and language data were found.")
    result = subprocess.run(
        [tesseract, str(image_path), "stdout", "-l", language, "tsv"],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=120,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or "unknown Tesseract error"
        raise RuntimeError(f"OCR fallback failed: {detail}")
    words: list[str] = []
    confidences: list[float] = []
    for row in csv.DictReader(io.StringIO(result.stdout), delimiter="\t"):
        text = (row.get("text") or "").strip()
        if text:
            words.append(text)
            try:
                confidence = float(row.get("conf") or "-1")
            except ValueError:
                confidence = -1
            if confidence >= 0:
                confidences.append(confidence)
    return " ".join(words), (sum(confidences) / len(confidences) if confidences else None)


def _pdf_images(path: Path, max_items: int, destination: Path) -> list[tuple[str, Path]]:
    pdftoppm = shutil.which("pdftoppm")
    if not pdftoppm:
        raise RuntimeError("PDF OCR unavailable: no compatible PDF rasterizer was found.")
    prefix = destination / "pdf-page"
    result = subprocess.run(
        [pdftoppm, "-f", "1", "-l", str(max_items), "-png", str(path), str(prefix)],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=180,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or "unknown pdftoppm error"
        raise RuntimeError(f"PDF rasterization for OCR failed: {detail}")
    def page_number(image: Path) -> int:
        match = re.search(r"-(\d+)$", image.stem)
        return int(match.group(1)) if match else 0

    images = sorted(destination.glob("pdf-page-*.png"), key=page_number)
    return [(f"PDF page {page_number(image)}", image) for image in images]


def _ooxml_images(path: Path, max_items: int, destination: Path) -> list[tuple[str, Path]]:
    prefix = OOXML_MEDIA_PREFIXES.get(path.suffix.lower())
    if not prefix:
        return []
    items: list[tuple[str, Path]] = []
    with zipfile.ZipFile(path) as archive:
        names = [name for name in archive.namelist() if name.startswith(prefix) and not name.endswith("/")]
        for index, name in enumerate(sorted(names)[:max_items], start=1):
            target = destination / Path(name).name
            target.write_bytes(archive.read(name))
            items.append((name, target))
    return items


def _ocr_image(image_path: Path, language: str) -> tuple[str, float | None, str]:
    try:
        text, confidence = _ocr_with_rapidocr(image_path)
        return text, confidence, "rapidocr"
    except Exception as rapidocr_error:
        try:
            text, confidence = _ocr_with_tesseract(image_path, language)
            return text, confidence, "tesseract"
        except Exception as tesseract_error:
            raise RuntimeError(
                "OCR fallback unavailable: neither RapidOCR nor a compatible Tesseract executable "
                "with the requested language data is available. "
                f"RapidOCR: {rapidocr_error}; Tesseract: {tesseract_error}"
            ) from tesseract_error


def ocr_fallback(path: Path, max_items: int, language: str) -> tuple[list[dict[str, object]], str]:
    if not 1 <= max_items <= 100:
        raise ValueError("OCR max items must be between 1 and 100.")
    with tempfile.TemporaryDirectory(prefix="codex-ocr-") as temporary:
        destination = Path(temporary)
        suffix = path.suffix.lower()
        if suffix == ".pdf":
            images = _pdf_images(path, max_items, destination)
        elif suffix in OOXML_MEDIA_PREFIXES:
            images = _ooxml_images(path, max_items, destination)
        elif suffix in IMAGE_EXTENSIONS:
            images = [(path.name, path)]
        else:
            return [], "not_applicable"
        results: list[dict[str, object]] = []
        for location, image in images:
            text, confidence, engine = _ocr_image(image, language)
            results.append(
                {
                    "location": location,
                    "text": text,
                    "confidence": round(confidence, 1) if confidence is not None else None,
                    "engine": engine,
                }
            )
    return results, "used" if results else "no_embedded_images"
