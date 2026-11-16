from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from documents.locate_markdown_extracts import locate_extracts


class SharedCapabilityTests(unittest.TestCase):
    def test_locate_extracts_distinguishes_current_and_stale_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            source = root / "source.txt"
            source.write_text("current", encoding="utf-8")
            digest = hashlib.sha256(source.read_bytes()).hexdigest()
            (root / "current.md").write_text(
                f"# TXT Converted Markdown\n\n- Source: `{source}`\n- Source SHA-256: `{digest}`\n- Extracted on: 2026-10-01 12:34:56\n",
                encoding="utf-8",
            )
            (root / "stale.md").write_text(
                f"# TXT Converted Markdown\n\n- Source path: {source}\n- Source SHA-256: {'0' * 64}\n",
                encoding="utf-8",
            )
            (root / "combined.md").write_text(
                f"# Combined\n\n## Sources\n- `{source}` (txt, SHA-256 `{digest}`)\n",
                encoding="utf-8",
            )

            result = locate_extracts([root], source=source)

            self.assertEqual([item["status"] for item in result["candidates"]], ["current", "current", "stale"])
            self.assertEqual(result["candidates"][0]["match_reasons"], ["source_path", "source_sha256", "source_filename"])



if __name__ == "__main__":
    unittest.main()
