"""Opt-in local metadata only; every telemetry failure leaves Jev unchanged."""
from __future__ import annotations

from contextlib import closing, contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sqlite3
import time
import uuid

CONFIG_NAME = "jev-monitor.json"
MODEL = re.compile(r"jev-[a-z0-9][a-z0-9.-]{0,48}\Z")
REASONS = frozenset(("all_candidates_required", "invalid_credential", "missing_credential", "credential_file_unreadable", "credential_file_permissions", "invalid_model", "invalid_request", "invalid_question", "invalid_choice", "invalid_score", "invalid_noul", "invalid_question_type", "request_too_large", "invalid_response", "invalid_rank_input", "response_too_large", "network_unavailable", "local_operation_unavailable", "cancelled"))
CURRENT = ContextVar("jev_observation", default=None)
SOURCE = ContextVar("jev_observation_source", default="python")


def now():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def number(value):
    return value if type(value) is int and 0 <= value <= 2**63 - 1 else None


def model(value):
    return value if isinstance(value, str) and MODEL.fullmatch(value) else None


def reason(value):
    return value if isinstance(value, str) and (value in REASONS or re.fullmatch(r"http_[1-5][0-9]{2}", value)) else "other"


def database():
    try:
        if os.environ.get("JEV_TELEMETRY", "").lower() in ("0", "off", "false"):
            return None
        root = Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex").expanduser()
        config = root / "monitoring" / CONFIG_NAME
        if config.stat().st_size > 8192:
            return None
        data = json.loads(config.read_text(encoding="utf-8"))
        if data.get("version") != 1 or data.get("enabled") is not True:
            return None
        path = Path(data["database"]).expanduser()
        return path if path.is_absolute() else None
    except Exception:
        return None


@contextmanager
def source(value):
    token = SOURCE.set(value if value in ("cli", "mcp", "python") else "python")
    try:
        yield
    finally:
        SOURCE.reset(token)


def emit(path, event):
    """One completed operation is one row, including all its HTTP attempts."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with closing(sqlite3.connect(path, timeout=0.08)) as connection, connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("CREATE TABLE IF NOT EXISTS jev_events (event_id TEXT PRIMARY KEY, timestamp TEXT NOT NULL, operation TEXT NOT NULL, status TEXT NOT NULL, input_tokens INTEGER, output_tokens INTEGER, latency_ms INTEGER NOT NULL, http_attempts INTEGER NOT NULL, request_bytes INTEGER NOT NULL, response_bytes INTEGER NOT NULL, response_unknown_attempts INTEGER NOT NULL, metadata TEXT NOT NULL)")
            connection.execute("CREATE INDEX IF NOT EXISTS jev_events_time ON jev_events(timestamp)")
            connection.execute("INSERT OR IGNORE INTO jev_events VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", (
                event["event_id"], event["timestamp"], event["operation"], event["status"], event["input_tokens"], event["output_tokens"], event["latency_ms"], len(event["attempts"]), sum(item["request_bytes"] for item in event["attempts"]), sum(item["response_bytes"] or 0 for item in event["attempts"]), sum(item["response_bytes"] is None for item in event["attempts"]), json.dumps(event, ensure_ascii=True, allow_nan=False, separators=(",", ":")),
            ))
        if os.name != "nt":
            os.chmod(path, 0o600)
    except Exception:
        pass


class Observation:
    def __init__(self, operation, requested_model):
        self.path = database()
        self.started = time.monotonic()
        self.event = {"version": 1, "event_id": uuid.uuid4().hex, "started_at": now(), "timestamp": None, "source": SOURCE.get(), "operation": operation, "requested_model": model(requested_model), "resolved_model": None, "status": "fallback", "reason": "other", "input_tokens": None, "output_tokens": None, "latency_ms": 0, "attempts": []}

    def __enter__(self):
        self.token = CURRENT.set(self if self.path else None)
        return self

    def complete(self, result):
        if isinstance(result, dict):
            status = result.get("status")
            self.event["status"] = status if status in ("ok", "fallback", "skipped", "dry_run") else "fallback"
            self.event["reason"] = reason(result.get("reason")) if result.get("reason") else None
            self.provider(result)

    def provider(self, result):
        if isinstance(result, dict):
            resolved = model(result.get("model"))
            if resolved:
                self.event["resolved_model"] = resolved
            usage = result.get("usage")
            if isinstance(usage, dict):
                for key in ("input_tokens", "output_tokens"):
                    value = number(usage.get(key))
                    if value is not None:
                        self.event[key] = value

    def __exit__(self, kind, error, traceback):
        try:
            if error is not None:
                self.event["status"] = "fallback"
                self.event["reason"] = "cancelled" if isinstance(error, (KeyboardInterrupt, SystemExit)) else reason(str(error))
            self.event["timestamp"] = now()
            self.event["latency_ms"] = max(0, round((time.monotonic() - self.started) * 1000))
            if self.path:
                emit(self.path, self.event)
        except Exception:
            pass
        finally:
            CURRENT.reset(self.token)
        return False


def observe(operation, requested_model=None):
    return Observation(operation, requested_model)


def provider(result):
    try:
        current = CURRENT.get()
        if current:
            current.provider(result)
    except Exception:
        pass


def attempt(started, request_bytes, response_bytes, status, http_status):
    try:
        current = CURRENT.get()
        if current:
            current.event["attempts"].append({"index": len(current.event["attempts"]) + 1, "latency_ms": max(0, round((time.monotonic() - started) * 1000)), "request_bytes": number(request_bytes) or 0, "response_bytes": number(response_bytes), "status": status if status in ("ok", "http_error", "network_unavailable", "invalid_response", "response_too_large") else "other", "http_status": http_status if type(http_status) is int and 100 <= http_status <= 599 else None})
    except Exception:
        pass
