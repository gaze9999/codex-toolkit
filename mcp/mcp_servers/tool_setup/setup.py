"""Copy shared installer resources into the wheel during build only."""
from pathlib import Path
import runpy

from setuptools import setup
from setuptools.command.build_py import build_py


class BuildSetup(build_py):
    def run(self):
        super().run()
        repo = Path(__file__).resolve().parents[3]
        helpers = runpy.run_path(str(repo / "mcp/scripts/prepare_mcp_release.py"))
        helpers["copy_installer_resources"](repo, Path(self.build_lib) / "codex_tool_setup/_setup")


setup(cmdclass={"build_py": BuildSetup})
