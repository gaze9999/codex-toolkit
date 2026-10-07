"""Launch the bundled official MCP with an isolated Edge profile."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from urllib.parse import urlparse


def edge_path(selected=None):
    if selected:
        candidates = [Path(selected).expanduser()]
    elif sys.platform == "win32":
        candidates = [Path(root) / "Microsoft/Edge/Application/msedge.exe" for root in (
            os.environ.get("ProgramFiles(x86)", "C:/Program Files (x86)"),
            os.environ.get("ProgramFiles", "C:/Program Files"),
            os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData/Local")),
        )]
    elif sys.platform == "darwin":
        candidates = [root / "Microsoft Edge.app/Contents/MacOS/Microsoft Edge" for root in (Path("/Applications"), Path.home() / "Applications")]
    else:
        candidates = [Path(path) for name in ("microsoft-edge", "microsoft-edge-stable") if (path := shutil.which(name))]
    for path in candidates:
        if path.is_file():
            return path.resolve()
    raise ValueError("Microsoft Edge is unavailable; install Edge or pass --executable-path with its existing executable")


def unpack_runtime(directory):
    resources = Path(__file__).parent
    pin = json.loads((resources / "upstream.json").read_text(encoding="utf-8"))
    data = (resources / "runtime.tgz").read_bytes()
    if pin.get("name") != "chrome-devtools-mcp" or pin.get("version") != "1.10.1" or len(data) > 10_000_000 or hashlib.sha256(data).hexdigest() != pin.get("sha256"):
        raise ValueError("Bundled official runtime checksum or version mismatch")
    target = Path(directory)
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as package:
        for member in package.getmembers():
            path = PurePosixPath(member.name)
            if path.is_absolute() or ".." in path.parts or "\\" in member.name or not path.parts or path.parts[0] != "package" or not (member.isfile() or member.isdir()) or member.size > 30_000_000:
                raise ValueError("Unsafe bundled runtime archive member")
            relative = PurePosixPath(*path.parts[1:])
            if not member.isfile() or not (relative.parts[:2] == ("build", "src") or str(relative) == "package.json"):
                continue
            destination = target.joinpath(*relative.parts)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(package.extractfile(member).read())
    return target


def command(args, runtime=None):
    node = args.node_path or shutil.which("node")
    if not node or not Path(node).is_file():
        raise ValueError("Node.js is unavailable; install a compatible runtime or pass --node-path")
    probe = subprocess.run([str(node), "--version"], capture_output=True, text=True, timeout=10, check=False)
    match = re.fullmatch(r"v(\d+)\.(\d+)\.(\d+)\s*", probe.stdout) if probe.returncode == 0 else None
    current = tuple(map(int, match.groups())) if match else (0, 0, 0)
    if not ((20, 19, 0) <= current < (21, 0, 0) or (22, 12, 0) <= current < (23, 0, 0) or current >= (23, 0, 0)):
        raise ValueError("Node.js must satisfy ^20.19.0, ^22.12.0 or >=23")
    upstream = runtime or Path(__file__).parent / "upstream"
    entry = upstream / "build/src/bin/chrome-devtools-mcp.js"
    metadata = json.loads((upstream / "package.json").read_text(encoding="utf-8"))
    if metadata.get("name") != "chrome-devtools-mcp" or metadata.get("version") != "1.10.1" or not entry.is_file():
        raise ValueError("Bundled official DevTools MCP is missing or has an unexpected version")
    flags = ["--no-usage-statistics", "--no-performance-crux"]
    if args.browser_url:
        url = urlparse(args.browser_url)
        if url.scheme != "http" or url.hostname not in {"127.0.0.1", "localhost", "::1"} or url.username or url.password or url.query or url.fragment or url.path not in {"", "/"}:
            raise ValueError("--browser-url requires a credential-free loopback HTTP debugging endpoint")
        flags += ["--browserUrl", args.browser_url]
    else:
        flags += ["--executablePath", str(edge_path(args.executable_path)), "--isolated"]
        if not args.headed:
            flags.append("--headless")
    return [str(Path(node).resolve()), str(entry), *flags]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--node-path", type=Path, help="Existing compatible Node.js executable")
    parser.add_argument("--executable-path", "--executablePath", type=Path, help="Existing Microsoft Edge executable")
    parser.add_argument("--headed", action="store_true", help="Show the isolated Edge window")
    parser.add_argument("--browser-url", help="Explicitly attach to an existing loopback debugging session")
    parser.add_argument("--check", action="store_true", help="Check prerequisites without launching a browser")
    args = parser.parse_args(argv)
    try:
        with tempfile.TemporaryDirectory(prefix="edg-") as directory:
            selected = command(args, unpack_runtime(directory))
            if args.check:
                print(json.dumps({"status": "ready", "upstream": "chrome-devtools-mcp", "version": "1.10.1", "node": selected[0], "browser": args.browser_url or selected[selected.index("--executablePath") + 1]}))
                return 0
            env = dict(os.environ, CHROME_DEVTOOLS_MCP_NO_UPDATE_CHECKS="1")
            process = subprocess.Popen(selected, env=env)
            try:
                return process.wait()
            finally:
                if process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()
    except KeyboardInterrupt:
        return 130
    except (OSError, ValueError, tarfile.TarError, subprocess.SubprocessError) as error:
        print("Edge DevTools MCP: " + str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
