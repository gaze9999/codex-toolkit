#!/usr/bin/env python3
"""Read an allowlisted activity summary from an explicitly selected loopback monitor."""
from __future__ import annotations

import argparse
import http.client
import json
import math
import re
import sys
from urllib.parse import urlsplit

WINDOWS = {"1h", "24h", "7d", "all"}
MAX_BYTES = 2 * 1024 * 1024
NAME = re.compile(r"[A-Za-z0-9_.:-]{1,128}")
HEALTH = {"ok", "healthy", "partial", "error", "unavailable", "missing", "stale", "disabled", "unknown", "degraded", "idle"}


def number(value):
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value >= 0 else None


def counters(value):
    if not isinstance(value, dict):
        return {}
    return {key: number(count) for key, count in value.items() if isinstance(key, str) and NAME.fullmatch(key)}


def health(value):
    return value if isinstance(value, str) and value in HEALTH else "unknown"


def project_summary(snapshot: dict, window: str) -> dict:
    if window not in WINDOWS or not isinstance(snapshot, dict) or snapshot.get("version") != 1:
        raise ValueError("Unsupported activity snapshot schema or window")
    codex = snapshot.get("codex") if isinstance(snapshot.get("codex"), dict) else {}
    jev = snapshot.get("jev") if isinstance(snapshot.get("jev"), dict) else {}
    usage = jev.get("summary") if isinstance(jev.get("summary"), dict) else {}
    mcp = snapshot.get("mcp") if isinstance(snapshot.get("mcp"), dict) else {}
    servers = []
    for server in mcp.get("servers", []) if isinstance(mcp.get("servers"), list) else []:
        if not isinstance(server, dict) or not isinstance(server.get("server"), str) or not NAME.fullmatch(server["server"]):
            continue
        servers.append({"server": server["server"], **{key: number(server.get(key)) for key in ("calls", "recognized", "returned", "errors", "average_ms", "p95_ms", "p99_ms")}})
    return {"schema_version": 1, "window": window,
            "codex": {"health": health(codex.get("health")), "tools": counters(codex.get("tools")), "nested_tools": counters(codex.get("nested_tools")),
                      **{key: number(codex.get(key)) for key in ("observed_tool_calls", "error_backfill_pending", "malformed_lines")}},
            "jev": {"health": health(jev.get("health")), **{key: number(usage.get(key)) for key in
                    ("calls", "http_attempts", "retries", "input_tokens", "output_tokens", "input_known_calls", "output_known_calls", "input_unknown_calls", "output_unknown_calls", "average_latency_ms")}, "statuses": counters(usage.get("statuses"))},
            "mcp": {"health": health(mcp.get("health")), "servers": servers},
            "scope": "local observations; unknown values preserved; no conversation details or account totals"}


def monitor_port(url: str) -> int:
    try:
        parsed = urlsplit(url)
        port = parsed.port
    except ValueError as exc:
        raise ValueError("Use an explicit HTTP loopback URL with a port") from exc
    if any(ord(char) < 32 for char in url) or parsed.scheme != "http" or parsed.hostname not in {"localhost", "127.0.0.1"} or parsed.username is not None or parsed.password is not None or parsed.path not in {"", "/"} or parsed.query or parsed.fragment or port is None or not 1 <= port <= 65535:
        raise ValueError("Use http://127.0.0.1:PORT without credentials, paths or parameters")
    return port


def fetch_summary(url: str, window: str) -> dict:
    if window not in WINDOWS:
        raise ValueError("Unsupported time window")
    connection = http.client.HTTPConnection("127.0.0.1", monitor_port(url), timeout=5)
    try:
        connection.request("GET", "/api/snapshot?window=" + window, headers={"Accept": "application/json"})
        response = connection.getresponse()
        if response.status != 200 or response.getheader("Content-Type", "").split(";", 1)[0].strip().lower() != "application/json":
            raise ValueError("Monitor did not return a supported JSON snapshot")
        raw = response.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise ValueError("Monitor snapshot exceeds the bounded response size")
        return project_summary(json.loads(raw), window)
    finally:
        connection.close()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True, help="Authorized, already-running HTTP loopback monitor with explicit port")
    parser.add_argument("--window", choices=sorted(WINDOWS), default="24h")
    args = parser.parse_args(argv)
    try:
        print(json.dumps(fetch_summary(args.url, args.window), ensure_ascii=False, indent=2, allow_nan=False))
        return 0
    except (OSError, ValueError, http.client.HTTPException):
        print("Activity summary unavailable; check the selected monitor, schema and response limit", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
