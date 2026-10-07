from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import unittest

from shared.tool_catalog import EXCLUDED_MODULES, TOOLS, TOOLS_BY_ID, ToolSpec, discover_tools
from shared.version import repository_version


class ToolCatalogTests(unittest.TestCase):
    def test_catalog_has_unique_importable_modules(self) -> None:
        self.assertGreaterEqual(len(TOOLS), 16)
        self.assertFalse(any(tool.module.startswith("mcp_tools.") for tool in TOOLS))
        self.assertEqual(len(TOOLS_BY_ID), len(TOOLS))
        self.assertTrue(EXCLUDED_MODULES.isdisjoint(tool.module for tool in TOOLS))
        for tool in TOOLS:
            with self.subTest(module=tool.module):
                self.assertIsNotNone(importlib.util.find_spec(tool.module))

    def test_repository_version_is_valid(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / "VERSION").write_text("0.3.0\n", encoding="utf-8")
            self.assertEqual(repository_version(root), "0.3.0")
            (root / "VERSION").write_text("invalid\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                repository_version(root)

    def test_new_main_module_is_discovered_without_catalog_edit(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            package = root / "new_tools"
            package.mkdir()
            (package / "convert_report.py").write_text(
                '"""Convert a report."""\n\ndef main():\n    return 0\n\n'
                'if __name__ == "__main__":\n    raise SystemExit(main())\n',
                encoding="utf-8",
            )
            (package / "helper.py").write_text("def helper():\n    return True\n", encoding="utf-8")

            tools = discover_tools(root)

        self.assertEqual([tool.module for tool in tools], ["new_tools.convert_report"])
        self.assertEqual(tools[0].category, "New Tools")

    def test_nested_module_and_discovery_error_are_reported(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            package = root / "reports" / "converters"
            package.mkdir(parents=True)
            (package / "nested.py").write_text(
                'if __name__ == "__main__":\n    raise SystemExit(0)\n',
                encoding="utf-8",
            )
            (package / "broken.py").write_text("def broken(:\n", encoding="utf-8")
            warnings: list[str] = []

            tools = discover_tools(root, warnings)

        self.assertEqual([tool.module for tool in tools], ["reports.converters.nested"])
        self.assertEqual(len(warnings), 1)
        self.assertIn("reports/converters/broken.py", warnings[0])
