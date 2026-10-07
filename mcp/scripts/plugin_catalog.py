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
SKIP = {"__pycache__", ".git", ".venv", "venv", "node_modules", "build", "dist", ".cache", ".tmp", "tmp", "temp", "tests", "test", "test-results", ".pytest_cache", ".mypy_cache", ".ruff_cache", "_workbench"}


def safe_source(root: Path, relative: str) -> Path:
    parts = PurePosixPath(relative)
    if not relative or relative != parts.as_posix() or parts.is_absolute() or ".." in parts.parts or "\\" in relative or ":" in relative:
        raise ValueError("Invalid package-relative path: " + relative)
    root = root.resolve()
    path = root.joinpath(*parts.parts)
    if not path.resolve().is_relative_to(root) or any(item.is_symlink() or getattr(item, "is_junction", lambda: False)() for item in (path, *path.parents) if item.is_relative_to(root)):
        raise ValueError("Source escapes its root or uses a link: " + relative)
    return path


def source_files(root: Path, relative: str):
    root = root.resolve()
    folder = safe_source(root, relative)
    if not folder.exists():
        raise ValueError("Missing plugin source: " + relative)
    for path in ([folder] if folder.is_file() else sorted(folder.rglob("*"))):
        parts = path.relative_to(root).parts
        if any(part.casefold() in SKIP or part.endswith(".egg-info") for part in parts) or path.suffix.lower() in {".pyc", ".pyo", ".zip", ".whl", ".log", ".tmp"}:
            continue
        safe_source(root, path.relative_to(root).as_posix())
        if path.is_file():
            if path.name.casefold() in {"auth.json", "credentials.json", "credentials", "id_rsa", "id_ed25519"} or path.name.casefold().startswith(".env") and path.name != ".env.example" or path.suffix.lower() in {".pem", ".key", ".p12", ".pfx"}:
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
        if not isinstance(entry.get("skills"), list):
            raise ValueError("Plugin Skills must be an array")
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
        components = entry.get("components", [])
        if not isinstance(components, list):
            raise ValueError("Plugin components must be an array")
        for component in components:
            if not isinstance(component, dict) or set(component) != {"source", "target"} or any(not isinstance(value, str) for value in component.values()):
                raise ValueError("Invalid plugin component mapping")
            if not safe_source(root, component["source"]).is_file():
                raise ValueError("Plugin component must select one file")
            safe_source(root, component["target"])
        bundles.append({**entry, "manifest": manifest, "manifest_source": manifest_path})
    return bundles


def payload(root: Path, bundle: dict) -> tuple[dict[str, bytes], dict]:
    root = root.resolve()
    files, sources = {}, {}

    def add(source: Path, target: str):
        safe_source(root, target)
        key = target.casefold()
        if key == "source-manifest.json" or any(key == name.casefold() or key.startswith(name.casefold() + "/") or name.casefold().startswith(key + "/") for name in files):
            raise ValueError("Duplicate plugin target: " + target)
        raw = source.read_bytes()
        files[target] = raw
        sources[target] = {"source": source.relative_to(root).as_posix(), "sha256": hashlib.sha256(raw).hexdigest()}

    add(safe_source(root, bundle["manifest_source"]), "plugin.json")
    if safe_source(root, "LICENSE").is_file():
        add(safe_source(root, "LICENSE"), "LICENSE")
    for skill in bundle["skills"]:
        for source, relative in source_files(root, "skills/" + skill):
            add(source, "skills/" + skill + "/" + relative)
    for resource in bundle["resources"]:
        if not isinstance(resource, dict) or set(resource) != {"source", "target"}:
            raise ValueError("Invalid plugin resource mapping")
        for source, relative in source_files(root, resource["source"]):
            add(source, resource["target"] + "/" + relative)
    for component in bundle.get("components", []):
        selected = list(source_files(root, component["source"]))
        if len(selected) != 1:
            raise ValueError("Plugin component was excluded by distribution rules")
        add(selected[0][0], component["target"])
    validate_components(files, bundle["manifest"])
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


def validate_components(files: dict[str, bytes], manifest: dict) -> None:
    """Validate packaged entry points without installing or invoking their contents."""
    overlay = manifest.get("extensions", {}).get("com.openai", {})
    if not isinstance(overlay, dict):
        raise ValueError("OpenAI extension must be an object")
    for field in ("apps", "hooks"):
        relative = overlay.get(field)
        if relative is None:
            continue
        if not isinstance(relative, str) or not relative.startswith("./") or ".." in PurePosixPath(relative).parts or relative[2:] not in files:
            raise ValueError("Unbundled plugin entry point: " + field)
        data = json.loads(files[relative[2:]])
        if not isinstance(data, dict) or not isinstance(data.get(field), dict) or not data[field]:
            raise ValueError("Plugin entry point needs a nonempty " + field + " object")
    if "mcp.json" in files:
        data = json.loads(files["mcp.json"])
        if not isinstance(data, dict) or data.get("$schema") != "https://agent-plugins.org/schemas/1.0.0/mcp.schema.json" or not isinstance(data.get("mcpServers"), dict) or not data["mcpServers"]:
            raise ValueError("Invalid portable MCP configuration")
        for server in data["mcpServers"].values():
            if not isinstance(server, dict) or server.get("type") not in {"stdio", "streamable-http", "sse"}:
                raise ValueError("Portable MCP server needs an explicit transport type")
            if server["type"] == "stdio" and not isinstance(server.get("command"), str) or server["type"] != "stdio" and not isinstance(server.get("url"), str):
                raise ValueError("Portable MCP server needs its command or URL")
    if not any(name.startswith("skills/") and name.endswith("/SKILL.md") for name in files) and "mcp.json" not in files and not overlay.get("apps"):
        raise ValueError("Plugin needs a Skill, MCP server or registered app mapping")


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
