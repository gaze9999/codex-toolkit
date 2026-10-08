import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "mcp/scripts"))

import check_development_tools as checker


class ToolVersionRequirements(unittest.TestCase):
    def test_playwright_cli_manifest_checks_its_reported_version(self):
        manifest = json.loads((ROOT / "mcp/tools/development-tools.requirements.json").read_text(encoding="utf-8"))
        requirement = next(
            item for item in manifest["tools"]["playwright"]["dependencies"]
            if item.get("command") == "playwright-cli"
        )
        self.assertEqual(requirement["minimum_version"], [0, 1, 22])
        self.assertEqual(requirement["version_args"], ["--version"])

    def test_playwright_cli_version_below_minimum_is_missing(self):
        requirement = {"command": "playwright-cli", "minimum_version": [0, 1, 22], "version_args": ["--version"]}
        with patch.object(checker, "find_command", return_value="playwright-cli"), patch.object(
            checker.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, "0.1.21\n", "")
        ):
            self.assertTrue(checker.dependency_missing(requirement, "windows"))

    def test_playwright_cli_minimum_and_newer_versions_are_accepted(self):
        requirement = {"command": "playwright-cli", "minimum_version": [0, 1, 22], "version_args": ["--version"]}
        for reported in ("0.1.22\n", "0.2.0\n"):
            with self.subTest(reported=reported), patch.object(
                checker, "find_command", return_value="playwright-cli"
            ), patch.object(
                checker.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, reported, "")
            ):
                self.assertFalse(checker.dependency_missing(requirement, "windows"))


if __name__ == "__main__":
    unittest.main()