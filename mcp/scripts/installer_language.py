"""Shared installer text with a conservative encoding fallback."""
import json
from pathlib import Path
import sys
import webbrowser
from urllib.parse import urlencode


class InstallerUi:
    def __init__(self, language="auto", *, encoding=None):
        self.data = json.loads((Path(__file__).resolve().parents[2]/"mcp/tools/installer.messages.json").read_text(encoding="utf-8"))
        if self.data.get("schema_version") != 1:
            raise ValueError("Unsupported installer language schema")
        encoding = encoding or getattr(sys.stdout, "encoding", None) or "utf-8"
        try:
            "".join(self.data["translations"]["zh-TW"].values()).encode(encoding, errors="strict")
            self.supports_chinese = True
        except (UnicodeError, LookupError):
            self.supports_chinese = False
        self.select(language)

    def select(self, language):
        if language not in {"auto", "zh-TW", "en"}:
            raise ValueError("Language must be auto, zh-TW or en")
        self.language = "zh-TW" if language != "en" and self.supports_chinese else "en"
        if language == "zh-TW" and not self.supports_chinese:
            print("Chinese output is unavailable in this encoding; using English")

    def text(self, template, *values):
        template = self.data["translations"].get(self.language, {}).get(template, template)
        return template.format(*values)

    def label(self, kind, value, fallback=None):
        label = self.data["labels"].get(self.language, {}).get(kind, {}).get(value, value)
        return label if self.language != "en" or label.isascii() else fallback or "Other"


def open_chinese_guide(root, tool, *, ui=None):
    ui = ui or InstallerUi()
    path = (root/"docs/setup/installer-guide.html").resolve()
    print(ui.text("Opening the Chinese setup guide: {0}", str(path)))
    try:
        if not path.is_file() or not webbrowser.open(path.as_uri()+"#"+urlencode({"tool": tool}), new=2):
            raise OSError("Guide or default browser unavailable")
    except OSError:
        print(ui.text("Could not open the guide automatically. Open it manually: {0}", str(path)))
