"""Verify one maintained token core and relocation without checkout dependencies."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "mcp" / "scripts"))
from prepare_plugin_release import prepare


def snapshot(root: Path) -> dict[str, str]:
    return {path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in root.rglob("*") if path.is_file()}


class TokenCountPluginTests(unittest.TestCase):
    def test_payload_keeps_canonical_core_and_focused_dependencies(self) -> None:
        packages, _ = prepare(ROOT, "documents-specifications")
        files, provenance = packages["documents-specifications"]
        self.assertEqual(files["resources/token-count/src/text/token_count.py"],
                         (ROOT / "python-tools/src/text/token_count.py").read_bytes())
        self.assertEqual(files["resources/token-count/requirements.txt"],
                         (ROOT / "python-tools/setup/requirements-token-count.txt").read_bytes())
        self.assertEqual(files["resources/token-count/VERSION"],
                         (ROOT / "python-tools/VERSION").read_bytes())
        manifest = json.loads((ROOT / "plugins/documents-specifications/plugin.json").read_text(encoding="utf-8"))
        self.assertEqual(provenance["version"], manifest["version"])
        for name in files:
            self.assertFalse(set(Path(name).parts) & {".venv", "tiktoken-cache", "__pycache__", ".git"})

    def test_standalone_skill_reports_missing_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            helper = Path(temporary) / "plugin/skills/token-count/scripts/count_tokens.py"
            helper.parent.mkdir(parents=True)
            helper.write_bytes((ROOT / "skills/token-count/scripts/count_tokens.py").read_bytes())
            result = subprocess.run([sys.executable, str(helper), "--text", "hello"],
                                    capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, b"")
        self.assertIn("缺少 Token Count 核心", result.stderr.decode("utf-8"))

    @unittest.skipUnless(importlib.util.find_spec("tiktoken"), "Exact counts require tiktoken")
    def test_relocated_payload_counts_and_exports_without_network_or_payload_writes(self) -> None:
        packages, _ = prepare(ROOT, "documents-specifications")
        files, _ = packages["documents-specifications"]
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary)
            plugin = work / "moved-plugin"
            for name, raw in files.items():
                target = plugin / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(raw)
            before = snapshot(plugin)
            helper = plugin / "skills/token-count/scripts/count_tokens.py"
            input_file = work / "貼上的文字 (1).txt"
            original = "hello world\r\n中文\r\n"
            input_file.write_bytes(b"\xef\xbb\xbf" + original.encode("utf-8"))
            output = work / "report.json"
            html = work / "tokens.html"
            script = '''
import runpy
import sys
from unittest.mock import patch
sys.argv = sys.argv[1:]
with patch('socket.socket.connect', side_effect=AssertionError('Network forbidden')):
    runpy.run_path(sys.argv[0], run_name='__main__')
'''
            env = {**os.environ, "PYTHONPATH": "", "PYTHONNOUSERSITE": "1"}
            result = subprocess.run([
                sys.executable, "-c", script, str(helper), "--input", str(input_file),
                "--output", str(output), "--html", str(html), "--json",
            ], cwd=work, env=env, capture_output=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr.decode("utf-8"))
            report = json.loads(result.stdout)
            import tiktoken

            expected = len(tiktoken.get_encoding("o200k_base").encode_ordinary(original))
            self.assertEqual(report["total_tokens"], expected)
            self.assertEqual(report["results"][0]["chars"], len(original))
            self.assertEqual(json.loads(output.read_text(encoding="utf-8")), report)
            self.assertIn("Token 彩色檢視", html.read_text(encoding="utf-8"))
            home = work / "home"
            home.mkdir()
            (work / ".git").mkdir()
            context = subprocess.run([
                sys.executable, "-c", script, str(helper), "context", "--project", str(work),
                "--codex-home", str(home), "--json",
            ], cwd=work, env=env, capture_output=True, timeout=30)
            self.assertEqual(context.returncode, 0, context.stderr.decode("utf-8"))
            self.assertEqual(json.loads(context.stdout)["total"], {"low": 13000, "high": 13000})
            self.assertEqual(snapshot(plugin), before)


if __name__ == "__main__":
    unittest.main()
