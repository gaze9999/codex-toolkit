"""Verify a native portable terminal CLI without a local Python dependency."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


def verify(executable: Path, *, launcher: list[str] | None = None) -> dict[str, object]:
    environment = dict(os.environ)
    for name in ("PYTHONHOME", "PYTHONPATH", "TIKTOKEN_CACHE_DIR"):
        environment.pop(name, None)
    environment["PATH"] = str(Path(environment.get("SystemRoot", "C:/Windows")) / "System32") if sys.platform == "win32" else "/usr/bin:/bin"
    with tempfile.TemporaryDirectory(prefix="portable-cli-") as temporary:
        command = launcher or [str(executable)]

        def call(arguments: list[str], expected: int = 0) -> str:
            result = subprocess.run(
                [*command, *arguments], cwd=temporary, env=environment,
                capture_output=True, text=True, encoding="utf-8", errors="replace",
                timeout=45,
            )
            if result.returncode != expected:
                raise RuntimeError(f"Portable CLI failed ({result.returncode}): {arguments[0]}: {result.stderr.strip()}")
            return result.stdout

        catalog = call(["--list"])
        if "documents.convert_to_markdown" not in catalog:
            raise RuntimeError("Portable CLI did not load the bundled tool catalog")
        tokens = json.loads(call(["text.tokenizer", "--text", "hello", "--json"]))
        if tokens.get("chars") != 5 or tokens.get("method") != "tiktoken":
            raise RuntimeError("Portable CLI tokenizer did not use its bundled offline encoding")
        source = Path(temporary) / "中文 source.txt"
        source.write_text("本機文件測試\nPortable CLI conversion\n", encoding="utf-8")
        call(["documents.convert_to_markdown", str(source)])
        markdown = source.with_suffix(".md")
        if not markdown.is_file() or "Portable CLI conversion" not in markdown.read_text(encoding="utf-8"):
            raise RuntimeError("Portable CLI did not convert the original local document")
        call(["scripts.release", "prepare", "--dry-run"], expected=2)
        call(["--web"], expected=2)
        return {
            "passed": True, "terminal": True, "document_conversion": True,
            "offline_tokenizer": True, "source_only_guard": True, "web_removed": True,
        }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("executable", type=Path)
    args = parser.parse_args(argv)
    executable = args.executable.expanduser().resolve()
    if not executable.is_file():
        parser.error("Provide the native portable CLI executable")
    print(json.dumps(verify(executable)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
