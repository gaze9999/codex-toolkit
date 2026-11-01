"""Explicit roots, immutable preview manifests and process-owned jobs."""
from __future__ import annotations

import hashlib
import json
import mimetypes
import secrets
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

ALLOWED = {".html", ".css", ".js", ".mjs", ".json", ".svg", ".png", ".jpg", ".jpeg", ".webp", ".woff2", ".gltf", ".glb", ".bin"}
MAX_FILE = 32 * 1024 * 1024


class Problem(ValueError):
    pass


class Workspace:
    def __init__(self, root):
        self.root = Path(root).resolve(strict=True)
        if not self.root.is_dir():
            raise Problem("invalid_root")

    def file(self, relative):
        if not isinstance(relative, str) or not relative or "\\" in relative or ":" in relative:
            raise Problem("invalid_relative_path")
        path = self.root / relative
        if Path(relative).is_absolute() or ".." in Path(relative).parts:
            raise Problem("invalid_relative_path")
        for item in (path, *path.parents):
            if item == self.root:
                break
            if item.is_symlink() or getattr(item, "is_junction", lambda: False)():
                raise Problem("linked_path")
        resolved = path.resolve(strict=True)
        if not resolved.is_relative_to(self.root) or not resolved.is_file():
            raise Problem("invalid_file")
        return resolved

    def read(self, relative, limit=MAX_FILE):
        path = self.file(relative)
        with path.open("rb") as stream:
            raw = stream.read(limit + 1)
        if len(raw) > limit:
            raise Problem("file_too_large")
        return raw

    def inspect(self):
        result = {"status": "ok", "root": str(self.root), "frameworks": [], "dependencies": {}, "versions": {}, "scripts": []}
        if (self.root / "package.json").exists():
            data = json.loads(self.read("package.json", 262144))
            if not isinstance(data, dict):
                raise Problem("invalid_package")
            dependencies = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
            candidates = {"@angular/core": "angular", "vue": "vue", "nuxt": "nuxt", "react": "react", "three": "three", "echarts": "echarts", "remotion": "remotion", "@react-three/fiber": "react-three-fiber"}
            result["dependencies"] = {name: dependencies[name] for name in candidates if name in dependencies}
            result["frameworks"] = [candidates[name] for name in candidates if name in dependencies]
            result["scripts"] = sorted(data.get("scripts", {}).keys())
        unity = self.root / "ProjectSettings/ProjectVersion.txt"
        if unity.exists():
            result["frameworks"].append("unity")
            result["versions"]["unity"] = self.read("ProjectSettings/ProjectVersion.txt", 4096).decode("utf-8").strip()
        result["available_operations"] = ["inspect", "artifacts", "preview_start", "preview_status", "preview_stop"]
        return result

    def artifacts(self, paths):
        if not isinstance(paths, list) or not 1 <= len(paths) <= 128:
            raise Problem("invalid_paths")
        rows = []
        for relative in paths:
            raw = self.read(relative)
            rows.append({"path": relative, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()})
        return {"status": "ok", "artifacts": rows}


class Previews:
    """Jobs live in this process only. Closing the owner closes its listeners."""
    def __init__(self, workspace):
        self.workspace = workspace
        self.jobs = {}
        self.lock = threading.RLock()

    def start(self, entry, files):
        if not isinstance(files, list) or not 1 <= len(files) <= 128 or entry not in files or len(set(files)) != len(files):
            raise Problem("invalid_manifest")
        # Snapshot only explicitly selected files; never serve project directories.
        assets, total = {}, 0
        for name in files:
            if not isinstance(name, str) or any(part.startswith(".") or part in {"node_modules", ".git"} for part in Path(name).parts) or Path(name).suffix.lower() not in ALLOWED:
                raise Problem("unsupported_asset")
            raw = self.workspace.read(name)
            total += len(raw)
            if total > 64 * 1024 * 1024:
                raise Problem("manifest_too_large")
            assets[name] = raw
        if Path(entry).suffix.lower() != ".html":
            raise Problem("invalid_entry")
        with self.lock:
            if len(self.jobs) >= 8:
                raise Problem("job_limit")
            token = secrets.token_urlsafe(24)
            prefix = "/" + token + "/"

            class Handler(BaseHTTPRequestHandler):
                def log_message(self, *args):
                    pass

                def do_GET(self):
                    self.serve(False)

                def do_HEAD(self):
                    self.serve(True)

                def serve(self, head):
                    host = self.headers.get("Host")
                    if host != "127.0.0.1:" + str(self.server.server_port):
                        self.send_error(403)
                        return
                    path = unquote(urlsplit(self.path).path)
                    name = path[len(prefix):] if path.startswith(prefix) else ""
                    if name not in assets:
                        self.send_error(404)
                        return
                    body = assets[name]
                    mime = "text/javascript" if name.endswith((".js", ".mjs")) else mimetypes.guess_type(name)[0] or "application/octet-stream"
                    self.send_response(200)
                    self.send_header("Content-Type", mime)
                    self.send_header("Content-Length", str(len(body)))
                    self.send_header("Cache-Control", "no-store")
                    self.send_header("X-Content-Type-Options", "nosniff")
                    self.send_header("Referrer-Policy", "no-referrer")
                    self.end_headers()
                    if not head:
                        self.wfile.write(body)

            server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
            thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
            job = secrets.token_hex(12)
            self.jobs[job] = (server, thread, entry, files, prefix)
            thread.start()
            return self.status(job)

    def status(self, job):
        with self.lock:
            if job not in self.jobs:
                return {"status": "unknown_job", "job_id": job}
            server, thread, entry, files, prefix = self.jobs[job]
            return {"status": "ready" if thread.is_alive() else "stopped", "job_id": job,
                    "url": f"http://127.0.0.1:{server.server_port}{prefix}{entry}", "files": files,
                    "snapshot": True, "owner": "current_process"}

    def stop(self, job):
        with self.lock:
            owned = self.jobs.pop(job, None)
        if owned is None:
            return {"status": "unknown_job", "job_id": job}
        server, thread, *_ = owned
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
        return {"status": "stopped", "job_id": job}

    def close(self):
        for job in list(self.jobs):
            self.stop(job)
