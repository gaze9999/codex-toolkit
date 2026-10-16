from __future__ import annotations

import contextlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from shared.tool_catalog import TOOLS_BY_ID
from text.token_count import count_file, count_text, main


def run_cli(arguments: list[str], stdin: str | None = None):
    stdout, stderr = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        if stdin is None:
            code = main(arguments)
        else:
            with patch("sys.stdin", io.StringIO(stdin)):
                code = main(arguments)
    return code, stdout.getvalue(), stderr.getvalue()


class TokenCountFailureTests(unittest.TestCase):
    def test_catalog_exposes_exact_command(self) -> None:
        self.assertEqual(TOOLS_BY_ID["token-count"].module, "text.token_count")

    def test_missing_dependency_is_an_error_without_estimates(self) -> None:
        with patch.dict(sys.modules, {"tiktoken": None}):
            code, stdout, stderr = run_cli(["--text", "hello", "--json"])
        self.assertEqual(code, 2)
        self.assertEqual(stdout, "")
        self.assertIn("pip install", stderr)

    def test_interactive_stdin_requires_explicit_input(self) -> None:
        with patch("sys.stdin.isatty", return_value=True):
            code, stdout, stderr = run_cli([])
        self.assertEqual(code, 2)
        self.assertEqual(stdout, "")
        self.assertIn("--input", stderr)

    def test_input_and_text_are_mutually_exclusive(self) -> None:
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
            main(["--input", "a.txt", "--text", "hello"])
        self.assertEqual(error.exception.code, 2)

    def test_existing_output_and_source_are_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "source.txt"
            path.write_bytes(b"original\r\n")
            for args in (["--text", "new"], ["--input", str(path)]):
                with self.subTest(args=args):
                    code, stdout, _ = run_cli([*args, "--output", str(path)])
                    self.assertEqual(code, 2)
                    self.assertEqual(stdout, "")
                    self.assertEqual(path.read_bytes(), b"original\r\n")

    def test_missing_or_invalid_utf8_input_does_not_create_output(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            invalid = root / "invalid.txt"
            invalid.write_bytes(b"\xff\xfe")
            output = root / "report.json"
            for path in (invalid, root / "missing.txt"):
                with self.subTest(path=path):
                    code, stdout, _ = run_cli(["--input", str(path), "--output", str(output)])
                    self.assertEqual(code, 2)
                    self.assertEqual(stdout, "")
                    self.assertFalse(output.exists())


@unittest.skipUnless(importlib.util.find_spec("tiktoken"), "Exact counts require tiktoken")
class ExactTokenCountTests(unittest.TestCase):
    def test_known_english_and_empty_counts(self) -> None:
        result = count_text("hello world")
        self.assertEqual(result["encoding"], "o200k_base")
        self.assertEqual(result["method"], "tiktoken")
        self.assertEqual(result["tokens"], 2)
        self.assertEqual(result["chars"], 11)
        self.assertEqual(result["utf8_bytes"], 11)
        self.assertEqual(result["chars_per_token"], 5.5)
        empty = count_text("")
        self.assertEqual(empty["tokens"], 0)
        self.assertIsNone(empty["chars_per_token"])

    def test_unicode_code_and_special_token_strings_match_literal_encoding(self) -> None:
        import tiktoken

        text = '# 測試 👩‍💻\r\nprint("hello")\n<|endoftext|>  '
        for encoding in ("o200k_base", "cl100k_base"):
            with self.subTest(encoding=encoding):
                result = count_text(text, encoding)
                expected = len(tiktoken.get_encoding(encoding).encode(text, disallowed_special=()))
                self.assertEqual(result["tokens"], expected)
                self.assertEqual(result["chars"], len(text))
                self.assertEqual(result["utf8_bytes"], len(text.encode("utf-8")))

    def test_bom_crlf_whitespace_and_empty_files(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "貼上的文字 (1).txt"
            for text in ("", "繁體中文\r\n\r\n  last\r\n"):
                with self.subTest(text=text):
                    path.write_bytes(b"\xef\xbb\xbf" + text.encode("utf-8"))
                    result = count_file(path)
                    self.assertEqual(result, {"source": str(path), **count_text(text)})

    def test_inline_json_and_plain_text_output(self) -> None:
        code, stdout, stderr = run_cli(["--text", "hello world", "--json"])
        self.assertEqual((code, stderr), (0, ""))
        self.assertEqual(json.loads(stdout)["total_tokens"], 2)
        code, stdout, _ = run_cli(["--text", ""])
        self.assertEqual(code, 0)
        self.assertIn("Token 數: 0", stdout)
        self.assertIn("無 (空文字)", stdout)

    def test_multiple_files_and_json_and_text_exports(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            first, second = root / "a.txt", root / "b.md"
            first.write_bytes(b"hello world")
            second.write_bytes("中文\r\n".encode("utf-8"))
            for name in ("report.json", "report.txt"):
                with self.subTest(name=name):
                    output = root / name
                    code, stdout, stderr = run_cli([
                        "--input", str(first), str(second), "--output", str(output),
                    ])
                    self.assertEqual((code, stderr), (0, ""))
                    self.assertEqual(output.read_bytes(), stdout.encode("utf-8"))
                    if output.suffix == ".json":
                        result = json.loads(stdout)
                        self.assertEqual(len(result["results"]), 2)
                        self.assertEqual(result["total_tokens"], 2 + count_file(second)["tokens"])
                    else:
                        self.assertIn("各來源分別計算後加總", stdout)

    def test_unknown_encoding_and_output_failure_have_nonzero_exit(self) -> None:
        code, stdout, stderr = run_cli(["--text", "hello", "--encoding", "missing-encoding"])
        self.assertEqual(code, 2)
        self.assertEqual(stdout, "")
        self.assertIn("missing-encoding", stderr)
        with tempfile.TemporaryDirectory() as temporary:
            code, stdout, _ = run_cli([
                "--text", "hello", "--output", str(Path(temporary) / "missing" / "report.json"),
            ])
            self.assertEqual(code, 2)
            self.assertEqual(stdout, "")

    def test_failed_batch_does_not_create_partial_report(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            first = root / "a.txt"
            first.write_bytes(b"hello")
            output = root / "report.json"
            code, stdout, _ = run_cli([
                "--input", str(first), str(root / "missing.txt"), "--output", str(output),
            ])
            self.assertEqual(code, 2)
            self.assertEqual(stdout, "")
            self.assertFalse(output.exists())

    def test_utf8_stdin_keeps_crlf_through_launcher(self) -> None:
        root = Path(__file__).resolve().parents[1]
        text = "中文\r\nhello\r\n"
        result = subprocess.run(
            [sys.executable, str(root / "launch-cli.py"), "token-count", "--json"],
            input=text.encode("utf-8"), capture_output=True, cwd=root, timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr.decode("utf-8"))
        actual = json.loads(result.stdout)["results"][0]
        self.assertEqual(actual, {"source": "stdin", **count_text(text)})


if __name__ == "__main__":
    unittest.main()
