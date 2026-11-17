import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class MarkdownReferenceTest(unittest.TestCase):
    def test_local_anchors_deleted_targets_and_bounds(self):
        cli = Path(__file__).resolve().parents[1] / "src/documents/analyze_markdown_references.py"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "sub").mkdir()
            (root / "a.md").write_text(
                '[anchor](b.md#重複-1 "title") [missing](gone.md) [same](sub/b.md)\n'
                '`[code](b.md)`\n```md\n[fenced](b.md)\n```\n[external](https://example.com)\n',
                encoding="utf-8",
            )
            (root / "b.md").write_text("# 重複\n# 重複\n", encoding="utf-8")
            (root / "sub" / "b.md").write_text("# Different\n", encoding="utf-8")
            (root / "too-large.md").write_bytes(b"A" * (1024 * 1024 + 1))
            command = [sys.executable, "-B", str(cli), "--root", str(root)]
            args = ["--document", "a.md", "--document", "b.md", "--document", "sub/b.md",
                    "--affected", "b.md", "--affected", "gone.md"]
            result = json.loads(subprocess.check_output([*command, *args]))
            self.assertEqual([row["exists"] for row in result["references"]], [True, False, True])
            self.assertEqual([row["resolved_target"] for row in result["reverse_references"]], ["b.md", "gone.md"])
            escaped = subprocess.run([*command, "--document", "../outside.md"], capture_output=True, check=False)
            self.assertEqual(escaped.returncode, 2)
            partial = subprocess.run([*command, *args, "--document", "too-large.md"], capture_output=True, check=False)
            self.assertEqual(partial.returncode, 1)
            self.assertTrue(json.loads(partial.stdout)["partial"])
