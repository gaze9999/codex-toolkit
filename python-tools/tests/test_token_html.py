from __future__ import annotations

from html.parser import HTMLParser
import importlib.util
from pathlib import Path
import tempfile
import unittest

from text.token_html import colored_text, render_html, token_spans
from tests.test_token_count import run_cli


class ColoredTextParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.inside = False
        self.text = ""

    def handle_starttag(self, tag, attrs):
        if tag == "pre" and ("class", "colored") in attrs:
            self.inside = True

    def handle_endtag(self, tag):
        if tag == "pre":
            self.inside = False

    def handle_data(self, data):
        if self.inside:
            self.text += data


@unittest.skipUnless(importlib.util.find_spec("tiktoken"), "Requires tiktoken")
class TokenHtmlTests(unittest.TestCase):
    def test_byte_boundaries_roundtrip_and_unicode_gradients(self):
        text = "漢字 🦄 👩‍💻\r\n<|endoftext|>"
        spans = token_spans(text, "o200k_base")
        self.assertEqual(b"".join(bytes.fromhex(row["hex"]) for row in spans), text.encode("utf-8"))
        self.assertEqual(spans[-1]["end"], len(text.encode("utf-8")))
        page = render_html([("source", text)], "o200k_base")
        parser = ColoredTextParser()
        parser.feed(page)
        self.assertEqual(parser.text, text)
        self.assertIn("linear-gradient", colored_text(text, spans, 2000))
        self.assertNotIn("\ufffd", parser.text)
        self.assertIn(">👩‍💻</span>", page)

    def test_html_escapes_source_and_payload(self):
        text = '<script>alert("test")</script><img onerror="bad">'
        page = render_html([("<unsafe>", text)], "o200k_base")
        self.assertNotIn(text, page)
        self.assertIn("&lt;unsafe&gt;", page)
        self.assertEqual(page.count("<script>"), 1)

    def test_empty_and_truncated_unicode(self):
        page = render_html([("empty", "")], "o200k_base")
        self.assertIn("空文字 · 0 Token", page)
        text = "🦄 rest"
        shown = colored_text(text, token_spans(text, "o200k_base"), 1)
        self.assertNotIn("\ufffd", shown)
        self.assertNotIn("🦄", shown)

    def test_export_and_overwrite_protection(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "tokens.html"
            code, _, error = run_cli(["--text", "測試 👩‍💻", "--html", str(path)])
            self.assertEqual((code, error), (0, ""))
            original = path.read_bytes()
            code, _, _ = run_cli(["--text", "other", "--html", str(path)])
            self.assertEqual(code, 2)
            self.assertEqual(path.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
