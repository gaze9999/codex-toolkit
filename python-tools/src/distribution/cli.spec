# Standalone terminal CLI, without frontend assets or a browser runtime.
from pathlib import Path
import sys

root = Path(SPECPATH).parents[1]
source = root / "src"
sys.path.insert(0, str(source))
sys.path.insert(0, str(root / "packages/workspace_core"))
from shared.tool_catalog import TOOLS
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

resources = root / ".build-inputs/cli"
data = [
    (str(root / "VERSION"), "."),
    (str(resources / "catalog.json"), "shared/resources"),
    (str(resources / "tiktoken"), "tiktoken-cache"),
]
for package in ("docx", "pptx"):
    data += collect_data_files(package)
hidden = [tool.module for tool in TOOLS] + [
    "my_py_workspace_core", "pypdf", "pdfplumber", "openpyxl", "docx", "pptx", "tiktoken", "tiktoken_ext.openai_public",
]
hidden += collect_submodules("my_py_workspace_core")
analysis = Analysis(
    [str(source / "distribution/cli_entry.py")],
    pathex=[str(source), str(root / "packages/workspace_core")],
    hookspath=[str(source / "distribution/hooks")],
    binaries=[], datas=data, hiddenimports=hidden,
    excludes=["webview", "tkinter", "PyQt5", "PyQt6", "PySide2", "PySide6"],
    noarchive=False,
)
pyz = PYZ(analysis.pure)
executable = EXE(pyz, analysis.scripts, [], exclude_binaries=True, name="launch-cli", console=True, upx=False)
collection = COLLECT(executable, analysis.binaries, analysis.datas, strip=False, upx=False, name="MyPyToolsCLI")
