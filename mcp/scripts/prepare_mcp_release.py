#!/usr/bin/env python3
"""Build and verify the Codex MCP server wheels for a repository release."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
import urllib.request
import zipfile


PRODUCER = "codex-setup.prepare_mcp_release.v1"
MANIFEST = "mcp-release-manifest.json"
PROJECTS = (
    (Path("python-tools"), "my-py-document-core", (Path("python-tools/pyproject.toml"), Path("python-tools/src"))),
    (Path("python-tools/packages/workspace_core"), "my-py-workspace-core", (Path("python-tools/packages/workspace_core"),)),
    (Path("mcp"), "codex-local-documents-mcp", (Path("mcp/pyproject.toml"), Path("mcp/mcp_servers/local_documents"))),
    (Path("mcp/mcp_servers/workspace_inspection"), "codex-workspace-inspection-mcp", (Path("mcp/mcp_servers/workspace_inspection"),)),
    (Path("mcp/mcp_servers/development_tools"), "codex-development-tools-mcp", (Path("mcp/mcp_servers/development_tools"),)),
    (Path("mcp/mcp_servers/edge_devtools"), "codex-edge-devtools-mcp", (Path("mcp/mcp_servers/edge_devtools"),)),
    (Path("skills/jev-evaluation"), "codex-jev-mcp", (Path("skills/jev-evaluation"),)),
    (Path("mcp/mcp_servers/tool_setup"), "codex-tool-setup", (Path("mcp/mcp_servers/tool_setup"),)),
)
INSTALLER_FILES = (
    "README.md", "LICENSE", "VERSION", "plugins/catalog.json",
    "tooling/package.py", "tooling/evaluate.py", "tooling/products.json",
    "evals/routing.json", "evals/benchmark.json", "docs/operating-model.md",
    "mcp/scripts/prepare_release.py",
    "mcp/mcp_servers/presets/baseline.json",
    "launch-cli.cmd", "launch-cli.ps1", "launch-cli.sh",
    "docs/README.md", "docs/agents.md", "docs/skills.md", "docs/third-party.md", "docs/setup/cli.md", "docs/tools/selection.md",
    "docs/usage/local-documents.md", "docs/usage/jev.md", "docs/plugins.md", "docs/mcp.md",
    "mcp/scripts/launch/install-mcp.cmd", "mcp/scripts/launch/install-mcp.ps1", "mcp/scripts/launch/install-mcp.sh",
    "mcp/scripts/launch/uninstall-mcp.cmd", "mcp/scripts/launch/uninstall-mcp.ps1", "mcp/scripts/launch/uninstall-mcp.sh", "mcp/scripts/uninstall_mcp.py",
    "mcp/scripts/launch/bootstrap-mcp.cmd", "mcp/scripts/launch/bootstrap-mcp.sh",
    "mcp/scripts/cli_runtime.ps1", "mcp/scripts/render_desktop_settings.py",
    "mcp/scripts/install_global_agents.py", "mcp/scripts/audit_skills.py", "mcp/scripts/restore_profile.py",
    "mcp/scripts/launch/install-development-tool.cmd", "mcp/scripts/launch/install-development-tool.ps1", "mcp/scripts/launch/install-development-tool.sh",
    "mcp/scripts/bootstrap_mcp.py", "mcp/scripts/check_development_tools.py", "mcp/scripts/install_development_tool.py",
    "mcp/scripts/update_development_tool.py", "mcp/scripts/installer_language.py", "mcp/scripts/installer_language.ps1",
    "mcp/scripts/plan_guard.py",
    "mcp/scripts/manager_registry.py",
    "mcp/scripts/manager_documents.py", "mcp/scripts/skill_versions.py",
    "mcp/scripts/probe_mcp.py", "mcp/scripts/sync_local_plugins.py", "mcp/scripts/manage_categories.py", "mcp/scripts/plugin_catalog.py", "mcp/scripts/prepare_plugin_release.py", "mcp/scripts/prepare_marketplace.py",
    "mcp/tools/installer.messages.json",
    "mcp/tools/development-tools.requirements.json", "mcp/tools/mcp-wheels.requirements.json",
    "docs/tools/development.md", "docs/tools/catalog.md", "docs/setup/packages.md",
    "docs/tools/proofreading.md", "docs/setup/installer-guide.html",
    "docs/tools/workflows.md", "docs/marketplace.md", "docs/restore.md",
    "mcp/tools/game-requirements/numpy.txt", "mcp/tools/game-requirements/pandas.txt",
    "mcp/tools/game-requirements/scipy.txt", "mcp/tools/game-requirements/sympy.txt",
    "mcp/tools/game-requirements/matplotlib.txt", "mcp/tools/game-requirements/hypothesis.txt",
    "mcp/tools/game-requirements/simpy.txt", "mcp/tools/game-requirements/optuna.txt",
    "mcp/tools/proofreading/zh-tw/.textlintrc.cjs", "mcp/tools/proofreading/zh-tw/taiwan-style.cjs",
    "mcp/tools/proofreading/zh-tw/terms.yml", "mcp/tools/proofreading/zh-tw/protected-copy.cjs",
    "mcp/tools/proofreading/ja/.textlintrc.json",
    "mcp/tools/proofreading/en/cspell.json",
    "mcp/tools/proofreading/textlint-mcp.cjs",
    "mcp/tools/serena/preferences.yml",
    "mcp/mcp_servers/development_tools/pyproject.toml", "mcp/mcp_servers/development_tools/README.md",
    "mcp/mcp_servers/development_tools/src/development_tool_mcp/__init__.py",
    "mcp/mcp_servers/development_tools/src/development_tool_mcp/server.py",
    "mcp/mcp_servers/edge_devtools/pyproject.toml", "mcp/mcp_servers/edge_devtools/setup.py",
    "mcp/mcp_servers/edge_devtools/upstream.json", "mcp/mcp_servers/edge_devtools/README.md",
    "mcp/mcp_servers/edge_devtools/MANIFEST.in",
    "mcp/mcp_servers/edge_devtools/src/edge_devtools_mcp/__init__.py",
    "mcp/mcp_servers/edge_devtools/src/edge_devtools_mcp/launcher.py",
)
VERSION = re.compile(r"v?(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?")
PROJECT_VERSION = re.compile(r'(?m)^version\s*=\s*"([^"]+)"\s*$')


def normalize_tag(value: str) -> str:
    if not VERSION.fullmatch(value):
        raise ValueError(f"Invalid release tag: {value}")
    return value if value.startswith("v") else "v" + value


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def normalize_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def upstream_specs(repo: Path) -> dict:
    path = repo / "mcp/tools/mcp-wheels.requirements.json"
    if not path.is_file():
        return {}
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != 1:
        raise ValueError("Unsupported upstream wheel schema")
    for spec in manifest["upstream"].values():
        if digest((repo / spec["license_file"]).read_bytes()) != spec["license_sha256"]:
            raise ValueError("Third-party license changed: " + spec["name"])
    return manifest["upstream"]


def copy_installer_resources(repo: Path, target: Path) -> None:
    for name in INSTALLER_FILES:
        path = target / name
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(repo / name, path)
    for folder in ('agents','skills','plugins'):
        for source in (repo/folder).rglob('*'):
            relative=source.relative_to(repo)
            if not source.is_file() or source.is_symlink() or any(part in {'__pycache__','dist','build','.git','.venv','venv'} or part.endswith('.egg-info') for part in relative.parts) or source.suffix in {'.pyc','.pyo','.whl','.zip'}:
                continue
            path=target/relative
            path.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(source,path)
    for folder in (target / "mcp/scripts", target / "mcp", target):
        (folder / "__init__.py").write_text("", encoding="utf-8")


def package_versions(repo: Path) -> dict[str, str]:
    versions = {}
    for relative, name, _sources in PROJECTS:
        match = PROJECT_VERSION.search((repo / relative / "pyproject.toml").read_text(encoding="utf-8"))
        if not match:
            raise ValueError(f"Package version not found: {repo / relative / 'pyproject.toml'}")
        versions[name] = match.group(1)
    for spec in upstream_specs(repo).values():
        versions[normalize_name(spec["name"])] = spec["version"]
    return versions


def source_hashes(repo: Path) -> dict[str, str]:
    files: set[Path] = set()
    for _relative, _name, sources in PROJECTS:
        for source in sources:
            path = repo / source
            files.update(path.rglob("*")) if path.is_dir() else files.add(path)
    files.update(repo / name for name in INSTALLER_FILES)
    for folder in ('agents','skills','plugins'):
        files.update((repo/folder).rglob('*'))
    files.add(repo / "mcp/scripts/prepare_mcp_release.py")
    files.add(repo / "mcp/mcp_servers/cwa_extended/launcher.py")
    files.add(repo / "docs/third-party.md")
    files.update(repo / spec["license_file"] for spec in upstream_specs(repo).values())
    result = {}
    for path in sorted(files, key=lambda item: item.as_posix().casefold()):
        if not path.is_file() or path.is_symlink() or any(part in {"build", "dist", "__pycache__", ".venv", ".git"} or part.endswith(".egg-info") for part in path.parts) or path.suffix in {'.pyc','.pyo','.whl','.zip'}:
            continue
        result[path.relative_to(repo).as_posix()] = digest(path.read_bytes())
    return result


def wheel_metadata(data: bytes) -> dict[str, str]:
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        if archive.testzip() is not None:
            raise ValueError("Wheel CRC validation failed")
        names = [name for name in archive.namelist() if name.endswith(".dist-info/METADATA")]
        if len(names) != 1:
            raise ValueError("Wheel must contain exactly one METADATA file")
        text = archive.read(names[0]).decode("utf-8")
    metadata = {}
    for field in ("Name", "Version"):
        match = re.search(rf"(?m)^{field}:\s*(.+)$", text)
        if not match:
            raise ValueError(f"Wheel metadata is missing {field}")
        metadata[field.casefold()] = normalize_name(match.group(1).strip()) if field == "Name" else match.group(1).strip()
    return metadata


def fetch_pinned(url: str, sha256: str, cache: Path, suffix: str) -> bytes:
    cache.mkdir(parents=True, exist_ok=True)
    path = cache / (sha256 + suffix)
    if path.is_file():
        data = path.read_bytes()
    else:
        with urllib.request.urlopen(url, timeout=60) as response:
            data = response.read()
        if digest(data) != sha256:
            raise ValueError("Downloaded package checksum mismatch")
        path.write_bytes(data)
    if digest(data) != sha256:
        raise ValueError("Cached package checksum mismatch: " + path.name)
    return data


def extract_source(data: bytes, target: Path) -> Path:
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        if archive.testzip() is not None:
            raise ValueError("Source archive CRC mismatch")
        roots = {name.split("/")[0] for name in archive.namelist()}
        if len(roots) != 1:
            raise ValueError("Source archive must have one root")
        for info in archive.infolist():
            destination = (target / info.filename).resolve()
            if not destination.is_relative_to(target.resolve()) or (info.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError("Unsafe source archive path")
        archive.extractall(target)
    return target / roots.pop()


def build_project(source: Path, wheels: Path) -> None:
    result = subprocess.run(
        [sys.executable, "-m", "pip", "wheel", "--no-cache-dir", "--no-deps", "--no-build-isolation", "--wheel-dir", str(wheels), str(source)],
        env=dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8", PATH=str(Path(sys.executable).parent) + os.pathsep + os.environ.get("PATH", "")),
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180, check=False,
    )
    if result.returncode:
        raise ValueError(f"MCP wheel build failed for {source.name}: {(result.stderr or result.stdout).strip()}")


def package_cwa(repo: Path, source: Path) -> None:
    project = tomllib.loads((source / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    package = source / "roc_cwa_mcp"
    package.mkdir()
    shutil.copytree(source / "src", package / "upstream")
    shutil.copyfile(repo / "mcp/mcp_servers/cwa_extended/launcher.py", package / "launcher.py")
    (package / "__init__.py").write_text("", encoding="utf-8")
    (source / "pyproject.toml").write_text(
        '[build-system]\nrequires = ["setuptools>=77", "wheel"]\nbuild-backend = "setuptools.build_meta"\n\n'
        '[project]\n' + '\n'.join(f'{key} = {json.dumps(project[key])}' for key in ("name", "version", "description", "readme", "requires-python")) + '\n'
        'dependencies = ["mcp[cli]>=1.6,<2", "requests>=2.28"]\nlicense-files = ["LICENSE"]\n\n'
        '[project.scripts]\nroc-cwa-mcp = "roc_cwa_mcp.launcher:main"\n\n'
        '[tool.setuptools]\npackages = ["roc_cwa_mcp"]\n\n'
        '[tool.setuptools.package-data]\nroc_cwa_mcp = ["upstream/*.py"]\n', encoding="utf-8",
    )


def build(repo: Path) -> dict[str, bytes]:
    with tempfile.TemporaryDirectory(prefix="codex-mcp-release-") as directory:
        temporary = Path(directory)
        source = temporary / "source"
        wheels = temporary / "wheels"
        shutil.copytree(
            repo,
            source,
            ignore=shutil.ignore_patterns(".git", ".github", ".codex", "tests", "test-results", "test-reports", "playwright-report", ".tmp", "tmp", "temp", ".venv", "venv", "node_modules", ".cache", "dist", "build", "__pycache__", "*.egg-info", "*.pyc", ".env", ".env.*"),
        )
        wheels.mkdir()
        for relative, _name, _sources in PROJECTS:
            build_project(source / relative, wheels)
        for name, spec in upstream_specs(repo).items():
            if spec["kind"] == "pypi":
                data = fetch_pinned(spec["url"], spec["sha256"], repo / ".cache/mcp-wheels", ".whl")
                (wheels / spec["filename"]).write_bytes(data)
            elif spec["kind"] == "source":
                data = fetch_pinned(spec["archive_url"], spec["archive_sha256"], repo / ".cache/mcp-wheels", ".zip")
                upstream = extract_source(data, temporary / ("upstream-" + name))
                if spec.get("layout") == "cwa_flat":
                    package_cwa(repo, upstream)
                build_project(upstream, wheels)
            else:
                raise ValueError("Unsupported upstream wheel source")
        built = {path.name: path.read_bytes() for path in sorted(wheels.glob("*.whl"))}
    seen = {metadata["name"]: metadata["version"] for metadata in map(wheel_metadata, built.values())}
    expected = package_versions(repo)
    if seen != expected:
        raise ValueError(f"Built MCP wheels do not match package projects: {seen!r} != {expected!r}")
    for name, data in built.items():
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            if any(part in {"tests", "test", "__tests__"} or part.startswith("test_") for path in archive.namelist() for part in path.split("/")):
                raise ValueError("Wheel contains local test files: " + name)
    return built


def make_zip(files: dict[str, bytes]) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data in sorted(files.items()):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, data)
    return output.getvalue()


def portable_assets(repo: Path, tag: str, wheels: dict[str, bytes]) -> dict[str, bytes]:
    files = {name: (repo / name).read_bytes() for name in INSTALLER_FILES}
    for folder in ('agents','skills','plugins'):
        for source in (repo/folder).rglob('*'):
            relative=source.relative_to(repo)
            if source.is_file() and not source.is_symlink() and not any(part in {'build','dist','__pycache__','.venv','.git'} or part.endswith('.egg-info') for part in relative.parts) and source.suffix not in {'.pyc','.pyo','.whl','.zip'}:
                files[relative.as_posix()]=source.read_bytes()
    files["README.md"] = (repo / "README.md").read_bytes()
    wheel_manifest = {
        "producer": PRODUCER, "tag": tag,
        "assets": [{"name": name, "size": len(data), "sha256": digest(data)} for name, data in sorted(wheels.items())],
    }
    files["wheels/mcp-release-manifest.json"] = (json.dumps(wheel_manifest, indent=2) + "\n").encode()
    files.update({"wheels/" + name: data for name, data in wheels.items()})
    notices = {spec["license_file"]: (repo / spec["license_file"]).read_bytes() for spec in upstream_specs(repo).values()}
    notices["docs/third-party.md"] = (repo / "docs/third-party.md").read_bytes()
    files.update(notices)
    return {f"mcp-installers-{tag}.zip": make_zip(files), f"third-party-notices-{tag}.zip": make_zip(notices)}


def prepare(repo: Path, tag: str, output_root: Path, dry_run: bool = False) -> dict[str, object]:
    repo = repo.resolve()
    tag = normalize_tag(tag)
    sources = source_hashes(repo)
    wheels = build(repo)
    extras = portable_assets(repo, tag, wheels)
    if source_hashes(repo) != sources:
        raise ValueError("Source changed during wheel preparation; review and rerun")
    all_assets = wheels | extras
    manifest = {
        "producer": PRODUCER,
        "tag": tag,
        "packages": package_versions(repo),
        "sources": sources,
        "assets": [{"name": name, "size": len(data), "sha256": digest(data)} for name, data in sorted(all_assets.items())],
    }
    output = output_root.resolve() / tag
    result = {"tag": tag, "output": str(output), "assets": len(wheels), "extra_assets": len(extras), "dry_run": dry_run}
    if dry_run:
        return result
    if output.exists():
        check_output(output, tag)
        shutil.rmtree(output)
    output.mkdir(parents=True)
    for name, data in all_assets.items():
        (output / name).write_bytes(data)
    (output / MANIFEST).write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def check_output(output: Path, tag: str) -> None:
    if output.is_symlink() or not output.is_dir():
        raise ValueError(f"MCP release output must be a regular directory: {output}")
    manifest = json.loads((output / MANIFEST).read_text(encoding="utf-8"))
    if manifest.get("producer") != PRODUCER or manifest.get("tag") != tag:
        raise ValueError("MCP release output belongs to another producer or tag")
    assets = manifest.get("assets")
    if not isinstance(assets, list) or {path.name for path in output.iterdir()} != {MANIFEST} | {item.get("name") for item in assets if isinstance(item, dict)}:
        raise ValueError("MCP release output contains missing or unmanaged files")
    for item in assets:
        path = output / item["name"]
        data = path.read_bytes()
        if len(data) != item.get("size") or digest(data) != item.get("sha256"):
            raise ValueError(f"MCP release asset changed independently: {path.name}")


def verify(repo: Path, tag: str, output_root: Path) -> list[Path]:
    tag = normalize_tag(tag)
    output = output_root.resolve() / tag
    manifest = json.loads((output / MANIFEST).read_text(encoding="utf-8"))
    if manifest.get("producer") != PRODUCER or manifest.get("tag") != tag:
        raise ValueError("MCP release manifest has the wrong producer or tag")
    if manifest.get("packages") != package_versions(repo) or manifest.get("sources") != source_hashes(repo):
        raise ValueError("MCP release manifest does not match current source")
    assets = manifest.get("assets")
    if not isinstance(assets, list) or {path.name for path in output.iterdir()} != {MANIFEST} | {item.get("name") for item in assets if isinstance(item, dict)}:
        raise ValueError("MCP release folder contains missing or unexpected files")
    paths = []
    seen = {}
    for item in assets:
        path = output / item["name"]
        data = path.read_bytes()
        if len(data) != item.get("size") or digest(data) != item.get("sha256"):
            raise ValueError(f"MCP release asset changed: {path.name}")
        if path.suffix == ".whl":
            metadata = wheel_metadata(data)
            if metadata["name"] in seen:
                raise ValueError("Duplicate wheel package")
            seen[metadata["name"]] = metadata["version"]
        elif path.suffix == ".zip":
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                if archive.testzip() is not None:
                    raise ValueError("Portable ZIP CRC mismatch")
        else:
            raise ValueError("Unexpected release asset type")
        paths.append(path)
    if seen != manifest["packages"]:
        raise ValueError("MCP wheel metadata does not match the manifest")
    wheels = {path.name: path.read_bytes() for path in paths if path.suffix == ".whl"}
    for name, expected in portable_assets(repo, tag, wheels).items():
        if (output / name).read_bytes() != expected:
            raise ValueError("Portable installer or notices differ from source")
    return sorted(paths)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tag")
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    try:
        result = prepare(args.repo, args.tag, args.output_dir or args.repo / "dist" / "mcp", args.dry_run)
    except (OSError, ValueError, json.JSONDecodeError, zipfile.BadZipFile) as error:
        print(f"FAIL {error}", file=sys.stderr)
        return 1
    print(f"{'PREVIEW' if args.dry_run else 'READY'} {result['tag']}; MCP wheels={result['assets']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
