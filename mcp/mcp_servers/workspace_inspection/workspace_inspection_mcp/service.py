"""Bound read-only access to workspace consistency and validation evidence APIs."""

from __future__ import annotations

import importlib.metadata
from pathlib import Path

from .core import load_core


class WorkspaceInspectionService:
    def __init__(self, read_roots: list[Path]):
        self.core = load_core()
        self.read_roots = tuple(self._root(path) for path in read_roots)
        if not self.read_roots:
            raise ValueError("At least one explicit read root is required")

    @staticmethod
    def _root(path: Path) -> Path:
        if not path.is_absolute() or not path.is_dir():
            raise ValueError("Roots must be existing absolute directories")
        return path.resolve()

    def directory(self, value: str) -> Path:
        path = Path(value).expanduser()
        if not path.is_absolute():
            raise ValueError("Use an absolute path")
        path = path.resolve(strict=True)
        if not path.is_dir() or not any(path.is_relative_to(root) for root in self.read_roots):
            raise ValueError("Directory is outside the configured read roots")
        return path

    def status(self) -> dict[str, object]:
        versions = {}
        for name in ("my-py-workspace-core", "mcp"):
            try:
                versions[name] = importlib.metadata.version(name)
            except importlib.metadata.PackageNotFoundError:
                versions[name] = None
        return {
            "status": "ready" if all(versions.values()) else "missing_dependencies",
            "versions": versions,
            "read_roots": [str(path) for path in self.read_roots],
            "read_only": True,
        }

    def validation_evidence(self, root: str, limit: int = 20, current: dict | None = None) -> dict[str, object]:
        if current is not None and not hasattr(self.core.validation, 'assess_evidence'):
            raise RuntimeError('Install my-py-workspace-core 0.2.0 for evidence validity checks')
        return self.core.validation.index_evidence(self.directory(root), limit, current) if current is not None else self.core.validation.index_evidence(self.directory(root), limit)

    def compare_environment(
        self,
        source: str,
        target: str,
        includes: list[str] | None = None,
        excludes: list[str] | None = None,
        use_default_excludes: bool = True,
        max_files: int = 20_000,
    ) -> dict[str, object]:
        exclude_patterns = tuple(excludes or ())
        if use_default_excludes:
            exclude_patterns = self.core.environment.DEFAULT_EXCLUDES + exclude_patterns
        return self.core.environment.compare_trees(
            self.directory(source),
            self.directory(target),
            includes=includes or (),
            excludes=exclude_patterns,
            max_files=max_files,
        )
