#!/usr/bin/env python3
"""Build a bundle release while preserving independent Skill versions."""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from skill_versions import VERSION

FRONTMATTER = re.compile(r"\A---\r?\n(.*?)\r?\n---(?=\r?\n|\Z)", re.DOTALL)
SKILL_NAME = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
PRODUCER = "codex-setup.prepare_release.v1"
MANIFEST = "release-manifest.json"
SKIP_DIRS = {"build", "dist", ".git", "__pycache__", ".venv", "venv", "node_modules", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".cache"}
SKIP_FILES = ("*.pyc", "*.pyo", "*.log", "*.tmp", "*.temp", "*.pem", "*.key", "*.swp", "*.swo", "*~", ".DS_Store", "Thumbs.db", "Desktop.ini")


def version_parts(value: str) -> tuple[int, int, int]:
    match = VERSION.fullmatch(value)
    if not match:
        raise ValueError(f"Invalid version: {value}; use X.Y.Z or vX.Y.Z")
    return tuple(map(int, match.groups()[:3]))


def skill_version(value: str) -> str:
    """Accept legacy v-prefixed values and store canonical SemVer."""
    version_parts(value)
    return value.removeprefix("v")


def normalize_version(value: str) -> str:
    version_parts(value)
    return value if value.startswith("v") else "v" + value


def scalar(block: str, key: str) -> str | None:
    match = re.search(rf"(?m)^[ \t]*{re.escape(key)}:[ \t]*([^\r\n]+)", block)
    if not match:
        return None
    value = match.group(1).strip()
    if value.startswith('"'):
        try:
            parsed, _ = json.JSONDecoder().raw_decode(value)
            return parsed if isinstance(parsed, str) else None
        except ValueError:
            raise ValueError(f"Invalid quoted value for {key}") from None
    if value.startswith("'"):
        match = re.match(r"'((?:[^']|'')*)'", value)
        if not match:
            raise ValueError(f"Invalid quoted value for {key}")
        return match.group(1).replace("''", "'")
    return re.split(r"\s+#", value, maxsplit=1)[0].strip() or None


def metadata_span(block: str) -> tuple[int, int] | None:
    matches = list(re.finditer(r"(?m)^metadata:[ \t]*(?:\r?\n|$)", block))
    if len(matches) > 1:
        raise ValueError("Duplicate metadata mapping")
    if not matches:
        if re.search(r"(?m)^metadata:", block):
            raise ValueError("Use an indented metadata mapping in SKILL.md")
        return None
    match = matches[0]
    next_key = re.search(r"(?m)^[^\s#]", block[match.end():])
    return match.end(), match.end() + next_key.start() if next_key else len(block)


def metadata_scalar(block: str, key: str) -> str | None:
    indents = re.findall(r"(?m)^([ ]+)\S[^:\r\n]*:", block)
    if not indents:
        return None
    indent = min(indents, key=len)
    match = re.search(rf"(?m)^{re.escape(indent)}{re.escape(key)}:[^\r\n]*", block)
    return scalar(match.group(), key) if match else None


def read_skill(path: Path) -> dict:
    original = path.read_bytes()
    text = original.decode("utf-8")
    match = FRONTMATTER.match(text)
    if not match:
        raise ValueError(f"Missing YAML frontmatter: {path}")
    block = match.group(1)
    if scalar(block, "name") != path.parent.name:
        raise ValueError(f"SKILL.md name must match its folder: {path.parent.name}")
    if not SKILL_NAME.fullmatch(path.parent.name) or len(path.parent.name) > 64:
        raise ValueError(f"Invalid skill folder name: {path.parent.name}")
    if not scalar(block, "description"):
        raise ValueError(f"Missing skill description: {path}")
    span = metadata_span(block)
    metadata = block[span[0]:span[1]] if span else ""
    return {"path": path, "original": original, "text": text, "match": match,
            "metadata": {key: metadata_scalar(metadata, key) for key in ("version", "author", "repository")}}


def update_skill(skill: dict, tag: str, defaults: dict[str, str]) -> bytes:
    match, text = skill["match"], skill["text"]
    block = match.group(1)
    newline = "\r\n" if "\r\n" in text else "\n"
    span = metadata_span(block)
    if span is None:
        block = block.rstrip("\r\n") + newline + "metadata:" + newline
        span = (len(block), len(block))
    section = block[span[0]:span[1]]
    fields = {"version": tag, **{key: value for key, value in defaults.items() if not skill["metadata"].get(key)}}
    indents = re.findall(r"(?m)^([ ]+)\S[^:\r\n]*:", section)
    indent = min(indents, key=len) if indents else "  "
    for key, value in fields.items():
        pattern = re.compile(rf"(?m)^{re.escape(indent)}{re.escape(key)}:[^\r\n]*")
        matches = list(pattern.finditer(section))
        if len(matches) > 1:
            raise ValueError(f"Duplicate metadata.{key}: {skill['path']}")
        line = f"{indent}{key}: {json.dumps(value, ensure_ascii=False)}"
        if matches:
            old = matches[0]
            comment = re.search(r"\s+#.*$", old.group())
            line += comment.group() if comment else ""
            section = section[:old.start()] + line + section[old.end():]
        else:
            section = section.rstrip("\r\n") + (newline if section else "") + line + newline
    block = block[:span[0]] + section + block[span[1]:]
    return (text[:match.start(1)] + block.rstrip("\r\n") + text[match.end(1):]).encode("utf-8")


def update_interface(original: bytes, tag: str) -> bytes:
    text = original.decode("utf-8")
    interface = re.search(r"(?m)^interface:[ \t]*\r?\n((?:[ \t]+[^\r\n]*(?:\r?\n|$))*)", text)
    if not interface:
        raise ValueError("Missing interface mapping in agents/openai.yaml")
    section = interface.group(1)
    lines = list(re.finditer(r"(?m)^([ ]+)display_name:[^\r\n]*", section))
    if len(lines) != 1:
        raise ValueError("Expected one interface.display_name in agents/openai.yaml")
    line = lines[0]
    name = scalar(line.group(), "display_name")
    if not name:
        raise ValueError("Missing interface.display_name in agents/openai.yaml")
    name = re.sub(r" \(v\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?\)$", "", name)
    revised = f'{line.group(1)}display_name: {json.dumps(f"{name} ({tag})", ensure_ascii=False)}'
    comment = re.search(r"\s+#.*$", line.group())
    revised += comment.group() if comment else ""
    start, end = interface.start(1) + line.start(), interface.start(1) + line.end()
    return (text[:start] + revised + text[end:]).encode("utf-8")


def git_output(repo: Path, *args: str) -> str | None:
    if not (repo / ".git").exists():
        return None
    try:
        result = subprocess.run(["git", "-c", f"safe.directory={repo.as_posix()}", "-C", str(repo), *args],
                                capture_output=True, text=True, encoding="utf-8", timeout=15)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return result.stdout if result.returncode == 0 else None


def ignored(path: Path) -> bool:
    return (bool(SKIP_DIRS.intersection(path.parts))
            or any(part.endswith(".egg-info") for part in path.parts)
            or (path.name.startswith(".env") and path.name != ".env.example")
            or any(fnmatch.fnmatch(path.name, pattern) for pattern in SKIP_FILES))


def snapshot(repo: Path, skills: list[dict]) -> dict[str, tuple[Path, bytes]]:
    listed = git_output(repo, "ls-files", "--cached", "--others", "--exclude-standard", "-z", "--", "skills")
    allowed = set(listed.split("\0")) if listed is not None else None
    files = {}
    for skill in skills:
        root = skill["path"].parent
        for directory, dirs, names in os.walk(root, followlinks=False):
            current = Path(directory)
            if current.is_symlink() or not current.resolve().is_relative_to(root.resolve()):
                raise ValueError(f"Linked skill directory is unsupported: {current}")
            dirs[:] = [name for name in dirs if not ignored(Path(name))]
            for name in dirs:
                child = current / name
                if child.is_symlink() or not child.resolve().is_relative_to(root.resolve()):
                    raise ValueError(f"Linked skill directory is unsupported: {child}")
            for name in sorted(names):
                path = current / name
                relative = path.relative_to(repo).as_posix()
                if ignored(path.relative_to(root)) or (allowed is not None and relative not in allowed):
                    continue
                if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
                    raise ValueError(f"Linked skill file is unsupported: {path}")
                files[path.relative_to(repo / "skills").as_posix()] = (path, path.read_bytes())
        if f"{root.name}/SKILL.md" not in files:
            raise ValueError(f"Skill entrypoint is excluded from packaging: {root.name}")
    return files


def zip_bytes(files: dict[str, bytes], timestamp: tuple) -> bytes:
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, data in sorted(files.items()):
            info = zipfile.ZipInfo(name, timestamp)
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, data, compresslevel=9)
    data = stream.getvalue()
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        assert archive.testzip() is None
        assert len(archive.infolist()) == len(files) and set(archive.namelist()) == set(files)
        for name, expected in files.items():
            assert archive.read(name) == expected
    return data


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def check_output(output: Path, tag: str) -> None:
    if not output.exists():
        return
    if output.is_symlink() or not output.is_dir():
        raise ValueError(f"Output must be a regular directory: {output}")
    actual = {path.name for path in output.iterdir()}
    if not actual:
        return
    marker = output / MANIFEST
    if not marker.is_file() or marker.is_symlink():
        raise ValueError(f"Output contains unmanaged files; choose another --output-dir: {output}")
    previous = json.loads(marker.read_text(encoding="utf-8"))
    if not isinstance(previous, dict) or previous.get("producer") != PRODUCER or previous.get("tag") != tag:
        raise ValueError(f"Output belongs to another release process: {output}")
    if not isinstance(previous.get("assets"), list):
        raise ValueError(f"Invalid output manifest: {marker}")
    expected = {MANIFEST}
    for asset in previous["assets"]:
        if not isinstance(asset, dict) or not isinstance(asset.get("name"), str) or not isinstance(asset.get("sha256"), str):
            raise ValueError(f"Invalid output manifest: {marker}")
        name = asset["name"]
        if Path(name).name != name or "/" in name or "\\" in name or not name.endswith(".zip"):
            raise ValueError("Invalid generated asset name in output manifest")
        expected.add(name)
        path = output / name
        if path.exists() and (path.is_symlink() or not path.is_file() or digest(path.read_bytes()) != asset["sha256"]):
            raise ValueError(f"Generated archive was changed independently: {path}")
    if actual - expected:
        raise ValueError(f"Output contains unmanaged files: {sorted(actual - expected)}")


def atomic_write(path: Path, data: bytes) -> None:
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=path.name + ".", suffix=".tmp", delete=False) as file:
        temporary = Path(file.name)
        file.write(data)
    try:
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def prepare(repo: Path, version: str | None, output_root: Path, dry_run: bool = False) -> dict:
    repo = repo.resolve()
    root = repo / "skills"
    if not root.is_dir():
        raise ValueError(f"Skills directory not found: {root}")
    directories = [path for path in sorted(root.iterdir())
                   if path.is_dir() and not path.name.startswith(".") and (path / "SKILL.md").is_file()]
    for path in directories:
        if path.is_symlink() or path.resolve().parent != root.resolve():
            raise ValueError(f"Linked skill directory is unsupported: {path}")
    skills = [read_skill(path / "SKILL.md") for path in directories]
    if not skills:
        raise ValueError("No skills with SKILL.md found")
    versions = {skill["path"].parent.name: skill_version(skill["metadata"]["version"] or "0.1.0") for skill in skills}
    candidates = [tag for tag in (git_output(repo, "tag", "--list") or "").splitlines() if VERSION.fullmatch(tag)]
    base = max((version_parts(value) for value in candidates), default=(0, 0, 0))
    tag = normalize_version(version) if version is not None else f"v{base[0]}.{base[1]}.{base[2] + 1}"
    output_root = output_root.expanduser().resolve()
    if output_root.is_relative_to(root.resolve()) or root.resolve().is_relative_to(output_root / tag):
        raise ValueError("Release output must be outside the skills directory")
    output = output_root / tag
    check_output(output, tag)
    defaults = {}
    for key in ("author", "repository"):
        values = {skill["metadata"][key] for skill in skills if skill["metadata"][key]}
        if len(values) == 1:
            defaults[key] = values.pop()
    files = snapshot(repo, skills)
    revised = {skill["path"]: update_skill(skill, versions[skill["path"].parent.name], defaults) for skill in skills}
    for skill in skills:
        path = skill["path"].parent / "agents" / "openai.yaml"
        if path.is_file():
            relative = path.relative_to(root).as_posix()
            if relative not in files:
                raise ValueError(f"Skill UI metadata is excluded from packaging: {relative}")
            revised[path] = update_interface(files[relative][1], "v" + versions[skill["path"].parent.name])
    contents = {name: revised.get(path, data) for name, (path, data) in files.items()}
    timestamp = datetime.now(timezone.utc).timetuple()[:6]
    archives = {f"all-skills-{tag}.zip": zip_bytes(contents, timestamp)}
    manifest = {"producer": PRODUCER, "tag": tag, "skill_count": len(skills), "source_files": len(files),
                "skills": [skill["path"].parent.name for skill in skills], "skill_versions": versions,
                "assets": [{"name": name, "size": len(data), "sha256": digest(data)} for name, data in sorted(archives.items())]}
    result = {"base": "v" + ".".join(map(str, base)), "tag": tag, "skills": len(skills),
              "zip_count": len(archives), "output": str(output), "dry_run": dry_run}
    if dry_run:
        return result
    output_root.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(dir=output_root, prefix=".prepare-release-"))
    assert staging.resolve().parent == output_root.resolve()
    fresh, previous = staging / "new", staging / "previous"
    fresh.mkdir()
    changed = []
    moved_previous = False
    try:
        for name, data in archives.items():
            (fresh / name).write_bytes(data)
        (fresh / MANIFEST).write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        for path, original in files.values():
            if path.read_bytes() != original:
                raise ValueError(f"Source changed during packaging: {path}")
        check_output(output, tag)
        originals = {path: data for path, data in files.values()}
        for path, data in revised.items():
            if data != originals[path]:
                if path.read_bytes() != originals[path]:
                    raise ValueError(f"Source changed before version update: {path}")
                atomic_write(path, data)
                changed.append(path)
        if output.exists():
            output.rename(previous)
            moved_previous = True
        fresh.rename(output)
    except Exception:
        if moved_previous and not output.exists():
            previous.rename(output)
        for path in reversed(changed):
            if path.read_bytes() == revised[path]:
                atomic_write(path, originals[path])
        raise
    finally:
        if staging.exists():
            if staging.resolve().parent != output_root.resolve():
                raise ValueError("Temporary release directory moved outside its output root")
            shutil.rmtree(staging)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    choice = parser.add_mutually_exclusive_group()
    choice.add_argument("--version", help="Manual version, e.g. 0.5.0 or v0.5.0; default: increment patch.")
    choice.add_argument("--patch", action="store_true", help="Increment the highest local Git tag by 0.0.1 (default).")
    parser.add_argument("--repo", type=Path, help="Repository root; defaults to this script's parent repository.")
    parser.add_argument("--output-dir", type=Path, help="Release output root; default: <repo>/dist. Each tag gets its own folder.")
    parser.add_argument("--dry-run", action="store_true", help="Validate and preview without modifying versions or writing files.")
    args = parser.parse_args()
    repo = (args.repo or Path(__file__).resolve().parents[2]).expanduser().resolve()
    output_root = args.output_dir or repo / "dist"
    try:
        result = prepare(repo, args.version, output_root, args.dry_run)
    except (OSError, ValueError, AssertionError) as error:
        print(f"FAIL {error}", file=sys.stderr)
        return 1
    print(f"{'PREVIEW' if args.dry_run else 'READY'} {result['base']} -> {result['tag']}; "
          f"skills={result['skills']} ZIPs={result['zip_count']}")
    print(f"OUTPUT {result['output']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
