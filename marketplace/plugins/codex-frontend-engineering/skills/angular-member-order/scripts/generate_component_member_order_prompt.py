#!/usr/bin/env python3
"""Generate a scoped handoff prompt for Angular component member ordering."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable


DEFAULT_PATTERNS = ("**/*.component.ts",)
EXCLUDED_PARTS = {
    ".angular",
    ".git",
    ".nx",
    "coverage",
    "dist",
    "node_modules",
    "tmp",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scan Angular components and generate a member-ordering prompt",
    )
    parser.add_argument("target", type=Path, help="Project, feature, or component path")
    parser.add_argument("--project-name", help="Name shown in the generated prompt")
    parser.add_argument(
        "--pattern",
        action="append",
        dest="patterns",
        help="Component glob, repeatable, default: **/*.component.ts",
    )
    parser.add_argument("--output", type=Path, help="Output file, otherwise stdout")
    parser.add_argument(
        "--signal-io",
        action="store_true",
        help="Include explicit Angular signal input/output migration requirements",
    )
    parser.add_argument(
        "--max-files",
        type=int,
        default=200,
        help="Maximum files allowed in one prompt, default: 200",
    )
    return parser.parse_args()


def is_excluded(path: Path) -> bool:
    return any(part.lower() in EXCLUDED_PARTS for part in path.parts)


def discover_components(target: Path, patterns: Iterable[str]) -> list[Path]:
    if target.is_file():
        return [target] if target.name.endswith(".component.ts") else []

    files: set[Path] = set()
    for pattern in patterns:
        for path in target.glob(pattern):
            if path.is_file() and not is_excluded(path.relative_to(target)):
                files.add(path)
    return sorted(files)


def format_file_list(target: Path, files: list[Path]) -> str:
    base = target if target.is_dir() else target.parent
    return "\n".join(f"- `{path.relative_to(base).as_posix()}`" for path in files)


def build_prompt(
    project_name: str,
    target: Path,
    files: list[Path],
    signal_io: bool,
) -> str:
    signal_requirements = ""
    if signal_io:
        signal_requirements = """

Signal I/O mode is explicitly authorized. Read the skill's `references/signal-io-migration.md`, verify the target Angular version, and migrate eligible `@Input` declarations to `input()` or `input.required()` and eligible `@Output` plus `EventEmitter` declarations to `output()`. Preserve binding names, aliases, payload types, defaults, optionality, and parent contracts. Update class and template reads to call input signals, remove obsolete imports, and handle setter inputs, direct child assignments, `ngOnChanges`, tests, and two-way bindings without changing behavior. Use `model()` only when separately requested. Leave any unsafe conversion unchanged and report it as an exception."""

    return f"""Use $angular-member-order to organize the Angular component class members in {project_name}.

Target files:
{format_file_list(target, files)}

Apply mode is authorized for these component files and the directly affected templates, focused tests, and callers required to preserve their existing bindings. Do not move or rename files and do not change unrelated behavior.

Order members by the skill's responsibility groups. Within the method area, group by actual screen section or complete feature flow rather than alphabetically. Within each flow, prefer event entry, operation, data loading, state synchronization, validation, then construction or transformation. Keep single-flow private helpers with that flow and shared private helpers near the class end.

Keep consecutive members in the same group together without extra blank lines and use one blank line between groups. Add one concise JSDoc heading per non-empty responsibility or feature group. Move existing decorators, JSDoc, and comments with their member, and do not rewrite, delete, merge, or reposition existing documentation relative to that member.

Preserve public interfaces and field-initializer dependency order. If the preferred ordering would change initialization or runtime behavior, keep the safe order and report the exception.{signal_requirements}

Review the final diff and run the smallest sufficient Angular type or compile check, relevant focused tests, and the repository's normal diff-whitespace check when available. Report changed files, ordering or migration exceptions, actual checks, blocked checks, and unverified boundaries. Do not claim unrun checks passed.
"""


def main() -> int:
    args = parse_args()
    target = args.target.resolve()
    if not target.exists():
        raise SystemExit(f"Target does not exist: {target}")
    if args.max_files < 1:
        raise SystemExit("--max-files must be greater than zero")

    files = discover_components(target, tuple(args.patterns or DEFAULT_PATTERNS))
    if not files:
        raise SystemExit("No matching *.component.ts files found")
    if len(files) > args.max_files:
        raise SystemExit(
            f"Found {len(files)} components, exceeding --max-files={args.max_files}; "
            "narrow the target or patterns"
        )

    prompt = build_prompt(
        args.project_name or target.stem,
        target,
        files,
        args.signal_io,
    )
    if args.output:
        output = args.output.resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(prompt, encoding="utf-8")
        print(output)
    else:
        print(prompt)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
