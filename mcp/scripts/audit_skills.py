#!/usr/bin/env python3
"""Audit repository skill metadata, links, Python syntax, and installed mirrors."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit
from skill_versions import SKILL_VERSION

FRONTMATTER_RE = re.compile(r"\A---\r?\n(.*?)\r?\n---(?:\r?\n|\Z)", re.DOTALL)
METADATA_RE = re.compile(r"(?m)^metadata:[ \t]*\n((?:[ \t]+[^\n]*(?:\n|$))*)")
RELEASE_TAG_RE = re.compile(r"v\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?")
LINK_RE = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
INLINE_PATH_RE = re.compile(r"`((?:scripts|references)/[^`\s]+)`")
ROOT_PATH_RE = re.compile(r"`((?:(?:docs|agents|mcp)/[A-Za-z0-9_./-]+|launch-[A-Za-z0-9_-]+\.(?:cmd|ps1|sh)))(?=[`\s])")
SKIP_PARTS = {"__pycache__"}


def scalar(text: str, key: str) -> str | None:
    match = re.search(rf"(?m)^\s*{re.escape(key)}:\s*(.+?)\s*$", text)
    return match.group(1).strip().strip("'\"") if match else None


def files(root: Path) -> dict[str, Path]:
    return {
        path.relative_to(root).as_posix(): path
        for path in root.rglob("*")
        if path.is_file() and not SKIP_PARTS.intersection(path.parts) and path.suffix != ".pyc"
    }


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit_skill(skill: Path, errors: list[str], release_tag: str | None = None) -> None:
    skill_file = skill / "SKILL.md"
    metadata_file = skill / "agents" / "openai.yaml"
    if not skill_file.is_file():
        errors.append(f"missing_skill:{skill.name}/SKILL.md")
        return
    text = skill_file.read_text(encoding="utf-8")
    version = None
    frontmatter = FRONTMATTER_RE.match(text)
    if not frontmatter:
        errors.append(f"frontmatter:{skill.name}/SKILL.md")
    else:
        block = frontmatter.group(1)
        name = scalar(block, "name")
        description = scalar(block, "description")
        if name != skill.name:
            errors.append(f"name:{skill.name}={name or 'missing'}")
        if not description or len(description) > 1024:
            errors.append(f"description:{skill.name}")
        metadata = METADATA_RE.search(block)
        metadata_block = metadata.group(1) if metadata else ""
        version = scalar(metadata_block, "version")
        if not version or not SKILL_VERSION.fullmatch(version):
            errors.append(f"metadata_version:{skill.name}={version or 'missing'}")
        if not scalar(metadata_block, "author"):
            errors.append(f"metadata_author:{skill.name}")
        repository = urlsplit(scalar(metadata_block, "repository") or "")
        if repository.scheme != "https" or not repository.netloc:
            errors.append(f"metadata_repository:{skill.name}")
    if not metadata_file.is_file():
        errors.append(f"missing_metadata:{skill.name}/agents/openai.yaml")
        return
    metadata = metadata_file.read_text(encoding="utf-8")
    display = scalar(metadata, "display_name")
    if not display or not version or not display.endswith(f" (v{version})"):
        errors.append(f"display_version:{skill.name}")
    short = scalar(metadata, "short_description")
    prompt = scalar(metadata, "default_prompt")
    if not short or not 25 <= len(short) <= 64:
        errors.append(f"short_description:{skill.name}={len(short or '')}")
    if not prompt or f"${skill.name}" not in prompt:
        errors.append(f"default_prompt:{skill.name}")


def audit_links(repo: Path, errors: list[str]) -> int:
    documents = [
        repo / "README.md",
        *sorted((repo / "agents").rglob("*.md")),
        *sorted((repo / "docs").rglob("*.md")),
        *sorted((repo / "skills").rglob("*.md")),
    ]
    checked = 0
    for document in documents:
        text = document.read_text(encoding="utf-8")
        for raw in LINK_RE.findall(text):
            target = raw.strip().strip("<>").split(maxsplit=1)[0]
            if not target or target.startswith(("#", "http://", "https://", "mailto:", "app://")):
                continue
            target = unquote(target.split("#", 1)[0].split("?", 1)[0])
            checked += 1
            if not (document.parent / target).resolve().exists():
                errors.append(f"link:{document.relative_to(repo).as_posix()}->{target}")
        relative = document.relative_to(repo)
        inline_root = repo / "skills" / relative.parts[1] if len(relative.parts) > 2 and relative.parts[0] == "skills" else document.parent
        for target in ROOT_PATH_RE.findall(text):
            if not Path(target).suffix or target == "agents/openai.yaml" and relative.parts[0] != "skills":
                continue  # Generic Skill metadata is checked per owner; install directories are not source files.
            checked += 1
            local = inline_root / target
            if not local.exists() and not (repo / target).exists():
                errors.append(f"inline_path:{relative.as_posix()}->{target}")
        for target in INLINE_PATH_RE.findall(text):
            checked += 1
            if not (inline_root / target).resolve().exists():
                errors.append(f"inline_path:{relative.as_posix()}->{target}")
    return checked


def positive_seconds(value: str) -> float:
    seconds = float(value)
    if not math.isfinite(seconds) or seconds <= 0:
        raise argparse.ArgumentTypeError("Timeout must be a positive finite number")
    return seconds


def audit_python(repo: Path, errors: list[str], help_timeout: float = 60, python_executable: str | None = None) -> int:
    scripts = sorted((repo / "skills").rglob("*.py")) + sorted((repo / "mcp/scripts").rglob("*.py"))
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    for script in scripts:
        try:
            compile(script.read_text(encoding="utf-8"), str(script), "exec")
        except SyntaxError as exc:
            errors.append(f"python:{script.relative_to(repo).as_posix()}:{exc.lineno}")
            continue
        try:
            result = subprocess.run(
                [python_executable or sys.executable, str(script), "--help"],
                cwd=script.parent,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                env=env,
                text=True,
                encoding="utf-8", errors="replace",
                timeout=help_timeout,
                check=False,
            )
        except subprocess.TimeoutExpired:
            errors.append(f"python_help:{script.relative_to(repo).as_posix()}:timeout")
            continue
        if result.returncode:
            stderr = result.stderr or ""
            detail = stderr.strip().splitlines()[-1] if stderr.strip() else f"exit {result.returncode}"
            errors.append(f"python_help:{script.relative_to(repo).as_posix()}:{detail}")
    return len(scripts)


def audit_mirrors(repo: Path, installed: Path, errors: list[str]) -> int:
    count = 0
    for source in sorted((repo / "skills").iterdir()):
        if not source.is_dir():
            continue
        target = installed / source.name
        count += 1
        if not target.is_dir():
            errors.append(f"mirror_missing:{source.name}")
            continue
        source_files = files(source)
        target_files = files(target)
        for relative in sorted(source_files.keys() - target_files.keys()):
            errors.append(f"mirror_missing:{source.name}/{relative}")
        for relative in sorted(target_files.keys() - source_files.keys()):
            errors.append(f"mirror_extra:{source.name}/{relative}")
        for relative in sorted(source_files.keys() & target_files.keys()):
            if digest(source_files[relative]) != digest(target_files[relative]):
                errors.append(f"mirror_diff:{source.name}/{relative}")
    return count


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit all custom skills with compact output.")
    parser.add_argument("--repo", type=Path, help="Repository root; defaults to this script's parent repository.")
    parser.add_argument("--installed-root", type=Path, help="Optional local skills mirror root.")
    parser.add_argument("--release-tag", help="Verify this prepared release manifest against the current independent Skill versions.")
    parser.add_argument("--python-help-timeout", type=positive_seconds, default=60,
                        help="Seconds allowed for each Python --help check (default: 60).")
    parser.add_argument("--python-executable", help="Compatible installed interpreter for script help checks; default is this interpreter")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    repo = (args.repo or Path(__file__).resolve().parents[2]).resolve()
    skill_root = repo / "skills"
    if not skill_root.is_dir():
        print("FAIL skills_root: skills directory not found")
        return 2

    errors: list[str] = []
    if not (repo / "agents" / "AGENTS.md").is_file():
        errors.append("missing_global:agents/AGENTS.md")
    if not (repo / "docs" / "agents.md").is_file():
        errors.append("missing_agent_guide:docs/agents.md")
    skills = sorted(path for path in skill_root.iterdir() if path.is_dir())
    for skill in skills:
        audit_skill(skill, errors, release_tag=args.release_tag)
    versions = set()
    for skill in skills:
        if not (skill / "SKILL.md").is_file():
            continue
        frontmatter = FRONTMATTER_RE.match((skill / "SKILL.md").read_text(encoding="utf-8"))
        metadata = METADATA_RE.search(frontmatter.group(1)) if frontmatter else None
        if metadata:
            versions.add(scalar(metadata.group(1), "version"))
    if args.release_tag:
        from release import verify
        try:
            verify(args.release_tag, repo=repo)
        except (OSError, ValueError, KeyError) as error:
            errors.append(f"release_manifest:{error}")
    links = audit_links(repo, errors)
    scripts = audit_python(repo, errors, args.python_help_timeout, args.python_executable)
    mirrors = audit_mirrors(repo, args.installed_root.resolve(), errors) if args.installed_root else 0
    result = {
        "status": "fail" if errors else "pass",
        "skills": len(skills),
        "links": links,
        "python_scripts": scripts,
        "mirrors": mirrors,
        "audit_python": sys.version.split()[0],
        "help_python": args.python_executable or sys.executable,
        "errors": errors,
    }
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif errors:
        print(f"FAIL skills={len(skills)} links={links} scripts={scripts} mirrors={mirrors} errors={len(errors)}")
        for error in errors:
            print(f"- {error}")
    else:
        print(f"PASS skills={len(skills)} links={links} scripts={scripts} mirrors={mirrors}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
