"""Guarded Markdown operations through the installed native markdown-checks CLI."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

BINARY_ENV = "LOCAL_DOCUMENTS_MARKDOWN_CHECKS"
TIMEOUT_SECONDS = 120


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def binary() -> str:
    """Explicit override first, then PATH; the CLI is installed from Toolkit tools/markdown-checks."""
    selected = os.environ.get(BINARY_ENV) or shutil.which("markdown-checks")
    if not selected or not Path(selected).is_file():
        raise RuntimeError(
            "Install markdown-checks (cargo install --locked --path <Toolkit>/tools/markdown-checks) "
            f"or set {BINARY_ENV} to its absolute path"
        )
    return selected


def run(*args: str) -> tuple[int, str, str]:
    result = subprocess.run([binary(), *args], capture_output=True, text=True, encoding="utf-8",
                            timeout=TIMEOUT_SECONDS, check=False)
    return result.returncode, result.stdout, result.stderr


def _json(code: int, stdout: str, stderr: str, accepted: tuple[int, ...] = (0,)) -> dict:
    if code in accepted and stdout.strip():
        return json.loads(stdout)
    message = stdout.strip() or stderr.strip()
    try:
        message = json.loads(message).get("message", message)
    except (ValueError, AttributeError):
        message = message.removeprefix("error: ")
    raise ValueError(message or f"markdown-checks exited with {code}")


def locate_extracts(roots: list[Path], *, source: Path | None, source_sha256: str | None,
                    limit: int, max_files: int) -> dict:
    args = ["locate-extracts", "--limit", str(limit), "--max-files", str(max_files)]
    for root in roots:
        args += ["--root", str(root)]
    if source is not None:
        args += ["--source", str(source)]
    if source_sha256:
        args += ["--source-sha256", source_sha256]
    return _json(*run(*args), accepted=(0, 1))


def inspect(path: Path, heading: str | None = None) -> dict:
    args = ["guarded", "--target-file", str(path), "inspect", "context"]
    if heading is not None:
        args += ["--section", heading]
    return _json(*run(*args))


def update(path: Path, content: str, expected_sha256: str, *, heading: str | None, entry_id: str | None,
           namespace: str, write: bool, in_place: bool) -> dict:
    with tempfile.TemporaryDirectory() as folder:
        content_file = Path(folder) / "content.md"
        content_file.write_text(content, encoding="utf-8", newline="")
        args = ["guarded", "--target-file", str(path), "--namespace", namespace]
        if heading is not None:
            args += ["replace", "context", "--section", heading]
        else:
            args += ["append", "history", "--entry-id", entry_id or ""]
        args += ["--content", str(content_file), "--expect", expected_sha256]
        if write:
            args.append("--write")
        if in_place:
            args.append("--in-place")
        return _json(*run(*args))


def write_guarded(path: Path, before: bytes, after: bytes) -> None:
    """Replace an existing Markdown output only while it still has the bytes read earlier."""
    with tempfile.TemporaryDirectory() as folder:
        content_file = Path(folder) / "content.md"
        content_file.write_bytes(after)
        code, stdout, stderr = run("sync-write", str(path), "--content-file", str(content_file),
                                   "--expected-sha256", sha(before))
    if code == 3:
        raise ValueError("Target changed during preparation; re-inspect and merge")
    if code != 0:
        raise ValueError((stderr or stdout).strip().removeprefix("ERROR: ") or "Guarded write failed")
    if path.read_bytes() != after:
        raise ValueError("Post-write mismatch: write may have occurred; inspect before retry")
