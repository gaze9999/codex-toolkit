"""Validate canonical plugin definitions and preview self-contained payloads in memory."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath
import re
from urllib.parse import unquote, urlsplit

SCHEMA = "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"
NAME = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
VERSION = re.compile(r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?")
LINK = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
SKIP = {"__pycache__", ".git", ".venv", "node_modules", "build", "dist", ".cache", ".tmp", ".pytest_cache", ".mypy_cache", ".ruff_cache"}


def safe_source(root: Path, relative: str) -> Path:
    parts = PurePosixPath(relative)
    if not relative or parts.is_absolute() or ".." in parts.parts or "\\" in relative or ":" in relative:
        raise ValueError("Invalid package-relative path: " + relative)
    root = root.resolve()
    path = root.joinpath(*parts.parts)
    if not path.resolve().is_relative_to(root) or any(item.is_symlink() for item in (path, *path.parents) if item.is_relative_to(root)):
        raise ValueError("Source escapes its root or uses a link: " + relative)
    return path


def source_files(root: Path, relative: str):
    folder = safe_source(root, relative)
    if not folder.exists():
        raise ValueError("Missing plugin source: " + relative)
    for path in ([folder] if folder.is_file() else sorted(folder.rglob("*"))):
        parts = path.relative_to(folder).parts if folder.is_dir() else ()
        if any(part in SKIP or part.endswith(".egg-info") for part in parts) or path.suffix in {".pyc", ".pyo", ".zip", ".whl", ".log", ".tmp"}:
            continue
        safe_source(root, path.relative_to(root).as_posix())
        if path.is_file():
            if path.name == "auth.json" or path.name.startswith(".env") and path.name != ".env.example" or path.suffix.lower() in {".pem", ".key"}:
                raise ValueError("Private material in plugin source")
            yield path, path.relative_to(folder).as_posix() if folder.is_dir() else folder.name


def load_catalog(root: Path) -> list[dict]:
    data = json.loads(safe_source(root, "plugins/catalog.json").read_text(encoding="utf-8"))
    if not isinstance(data, dict) or type(data.get("schema_version")) is not int or data.get("schema_version") != 1 or not isinstance(data.get("bundles"), list):
        raise ValueError("Invalid plugin catalog schema")
    setup = json.loads(safe_source(root, "mcp/tools/development-tools.requirements.json").read_text(encoding="utf-8"))
    baseline = json.loads(safe_source(root, "mcp/mcp_servers/presets/baseline.json").read_text(encoding="utf-8"))
    available_profiles = set(setup["tools"]) | {row["name"].replace("_", "-") for row in baseline["servers"]}
    ids, owners, bundles = set(), {}, []
    for entry in data["bundles"]:
        if not isinstance(entry, dict) or not isinstance(entry.get("batch"), str) or not entry["batch"]:
            raise ValueError("Invalid plugin batch definition")
        identifier = entry.get("id")
        if not isinstance(identifier, str) or not NAME.fullmatch(identifier) or identifier in ids:
            raise ValueError("Invalid or duplicate plugin ID")
        ids.add(identifier)
        if entry.get("status") not in {"ready", "blocked"} or entry.get("status") == "blocked" and (not isinstance(entry.get("blocked_reason"), str) or not entry["blocked_reason"].strip()):
            raise ValueError("Plugin availability needs an explicit reason")
        if not isinstance(entry.get("skills"), list) or not entry["skills"]:
            raise ValueError("Plugin must select at least one Skill")
        for skill in entry["skills"]:
            if not isinstance(skill, str) or not NAME.fullmatch(skill) or skill in owners:
                raise ValueError("A Skill needs one canonical bundle owner: " + str(skill))
            owners[skill] = identifier
            if not safe_source(root, "skills/" + skill + "/SKILL.md").is_file():
                raise ValueError("Missing Skill: " + skill)
        manifest_path = "plugins/" + identifier + "/plugin.json"
        manifest = json.loads(safe_source(root, manifest_path).read_text(encoding="utf-8"))
        if not isinstance(manifest, dict) or manifest.get("$schema") != SCHEMA or manifest.get("name") != "codex-" + identifier or not isinstance(manifest.get("version"), str) or not VERSION.fullmatch(manifest["version"]):
            raise ValueError("Invalid portable plugin manifest: " + identifier)
        if not isinstance(manifest.get("description"), str) or not manifest["description"].strip():
            raise ValueError("Missing plugin description")
        profiles = entry.get("runtime_profiles")
        if not isinstance(profiles, list) or any(not isinstance(name, str) or not NAME.fullmatch(name) or name not in available_profiles for name in profiles) or len(set(profiles)) != len(profiles):
            raise ValueError("Invalid optional runtime profiles")
        if not isinstance(entry.get("resources"), list):
            raise ValueError("Plugin resources must be an array")
        for resource in entry["resources"]:
            if not isinstance(resource, dict) or set(resource) != {"source", "target"} or any(not isinstance(value, str) for value in resource.values()):
                raise ValueError("Invalid plugin resource mapping")
            safe_source(root, resource["source"])
            safe_source(root, resource["target"])
        bundles.append({**entry, "manifest": manifest, "manifest_source": manifest_path})
    return bundles


def payload(root: Path, bundle: dict) -> tuple[dict[str, bytes], dict]:
    files, sources = {}, {}

    def add(source: Path, target: str):
        safe_source(root, target)
        if any(target.casefold() == name.casefold() for name in files):
            raise ValueError("Duplicate plugin target: " + target)
        raw = source.read_bytes()
        files[target] = raw
        sources[target] = {"source": source.relative_to(root).as_posix(), "sha256": hashlib.sha256(raw).hexdigest()}

    add(safe_source(root, bundle["manifest_source"]), "plugin.json")
    for skill in bundle["skills"]:
        for source, relative in source_files(root, "skills/" + skill):
            add(source, "skills/" + skill + "/" + relative)
    for resource in bundle["resources"]:
        if not isinstance(resource, dict) or set(resource) != {"source", "target"}:
            raise ValueError("Invalid plugin resource mapping")
        for source, relative in source_files(root, resource["source"]):
            add(source, resource["target"] + "/" + relative)
    for name, raw in files.items():
        if not name.endswith(".md"):
            continue
        for link in LINK.findall(raw.decode("utf-8")):
            target = link.strip().strip("<>").split(maxsplit=1)[0]
            if not target or target.startswith("#") or urlsplit(target).scheme:
                continue
            link_path = unquote(target.split("#", 1)[0].split("?", 1)[0])
            if PurePosixPath(link_path).is_absolute() or "\\" in link_path or ":" in link_path:
                raise ValueError("Nonportable plugin reference: " + name)
            parts = []
            for part in (PurePosixPath(name).parent / link_path).parts:
                if part == "..":
                    if not parts:
                        raise ValueError("Plugin reference escapes root: " + name)
                    parts.pop()
                elif part != ".":
                    parts.append(part)
            resolved = "/".join(parts)
            if resolved not in files and not any(path.startswith(resolved.rstrip("/") + "/") for path in files):
                raise ValueError("Unbundled reference: " + name + " -> " + target)
    return files, {"plugin": bundle["manifest"]["name"], "version": bundle["manifest"]["version"], "files": sources,
                   "runtime_profiles": bundle["runtime_profiles"], "runtime_policy": "existing setup; no automatic installation or duplicate MCP registration"}


def inventory(root: Path, settings: dict) -> list[dict]:
    rows = []
    configured = settings.get("plugins", {})
    if not isinstance(configured, dict):
        raise ValueError("Invalid Plugin configuration")
    represented = set()
    for bundle in load_catalog(root):
        name = bundle["manifest"]["name"]
        registrations = [key for key, value in configured.items() if key.split("@", 1)[0] == name and isinstance(value, dict)]
        represented.update(registrations)
        direct = [skill for skill in bundle["skills"] if skill in settings.get("_direct_skills", [])]
        rows.append({"id": bundle["id"], "name": name, "title": bundle["manifest"].get("extensions", {}).get("com.openai", {}).get("interface", {}).get("displayName", name),
                     "kind": "plugin", "protected": True, "version": bundle["manifest"]["version"], "batch": bundle["batch"],
                     "description": bundle["manifest"]["description"], "skills": bundle["skills"], "runtime_profiles": bundle["runtime_profiles"],
                     "availability": bundle["status"], "blocked_reason": bundle.get("blocked_reason"), "configured": registrations,
                     "enabled": any(configured[key].get("enabled", True) for key in registrations), "direct_skills": direct,
                     "state": "待授權" if bundle["status"] == "blocked" else "已設定" if registrations else "來源已定義", "loaded": None})
    rows.extend({"id": name, "name": name, "kind": "plugin", "protected": True, "state": "已啟用" if value.get("enabled", True) else "已停用", "loaded": None}
                for name, value in configured.items() if name not in represented and isinstance(value, dict))
    return rows
