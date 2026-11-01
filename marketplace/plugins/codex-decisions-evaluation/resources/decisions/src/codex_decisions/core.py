"""Validate bounded evidence and call only the official Decisions endpoint."""
from __future__ import annotations

import base64
import hashlib
import json
import math
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit

ENDPOINT = "https://api.openai.com/v1/decisions"
MAX_BYTES = 2 * 1024 * 1024
MAX_RESPONSE = 2 * 1024 * 1024
DEFAULT_CONFIG = {"credential_env": "OPENAI_API_KEY", "model": "gpt-6-luna", "timeout_seconds": 20}


class Problem(ValueError):
    """Safe machine-readable error; never embeds input or provider error text."""


def encode(value):
    try:
        return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode("utf-8")
    except (ValueError, TypeError, RecursionError, UnicodeError) as exc:
        raise Problem("invalid_json") from exc


def read_json(path: Path, limit=MAX_BYTES):
    with path.open("rb") as stream:
        raw = stream.read(limit + 1)
    if len(raw) > limit:
        raise Problem("input_too_large")
    try:
        return json.loads(raw.decode("utf-8-sig"), parse_constant=lambda _: (_ for _ in ()).throw(Problem("nonfinite_json")))
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise Problem("invalid_json") from exc


def fields(value, required, optional=()):
    if not isinstance(value, dict) or not set(required) <= value.keys() or value.keys() - set(required) - set(optional):
        raise Problem("invalid_fields")


def text(value, limit=65536):
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise Problem("invalid_text")


def config_from(path=None):
    config = dict(DEFAULT_CONFIG)
    if path is not None:
        supplied = read_json(Path(path), 4096)
        fields(supplied, (), DEFAULT_CONFIG)
        config.update(supplied)
    if not isinstance(config["credential_env"], str) or not re.fullmatch(r"[A-Z][A-Z0-9_]{0,63}", config["credential_env"]):
        raise Problem("invalid_credential_variable")
    text(config["model"], 128)
    timeout = config["timeout_seconds"]
    if type(timeout) not in (float, int) or not math.isfinite(timeout) or not 1 <= timeout <= 60:
        raise Problem("invalid_timeout")
    return config


def status(config):
    return {"status": "configured" if os.environ.get(config["credential_env"], "").strip() else "needs_credentials",
            "credential_env": config["credential_env"], "endpoint": ENDPOINT, "model": config["model"],
            "credential_checked": "presence_only", "online": False, "version": "0.1.0"}


def json_data(value):
    if not isinstance(value, dict) and not (isinstance(value, list) and all(isinstance(x, dict) for x in value)):
        raise Problem("invalid_json_evidence")
    if len(encode(value)) > 262144:
        raise Problem("json_evidence_too_large")
    stack, count = [(value, 1)], 0
    while stack:
        item, depth = stack.pop()
        count += 1
        if count > 10000 or depth > 32:
            raise Problem("json_evidence_limit")
        if isinstance(item, dict):
            stack.extend((x, depth + 1) for x in item.values())
        elif isinstance(item, list):
            stack.extend((x, depth + 1) for x in item)


def content(value, *, multimodal=True):
    if isinstance(value, str):
        text(value)
        return
    if not isinstance(value, list) or not 1 <= len(value) <= 64:
        raise Problem("invalid_content")
    for part in value:
        if not isinstance(part, dict):
            raise Problem("invalid_content_part")
        kind = part.get("type")
        if not isinstance(kind, str):
            raise Problem("invalid_content_part")
        if kind == "input_text":
            fields(part, ("type", "text"))
            text(part["text"])
        elif multimodal and kind == "input_json":
            fields(part, ("type", "data"))
            json_data(part["data"])
        elif multimodal and kind == "input_image":
            fields(part, ("type", "image_url"), ("detail",))
            url = part["image_url"]
            if not isinstance(url, str) or not isinstance(part.get("detail", "auto"), str) or part.get("detail", "auto") not in {"auto", "low", "high", "original"}:
                raise Problem("invalid_image")
            if url.startswith("data:"):
                match = re.fullmatch(r"data:image/(png|jpeg|webp);base64,([A-Za-z0-9+/=]+)", url)
                if not match:
                    raise Problem("invalid_image_data")
                try:
                    raw = base64.b64decode(match[2], validate=True)
                except ValueError as exc:
                    raise Problem("invalid_image_data") from exc
                valid = (match[1] == "png" and raw.startswith(b"\x89PNG\r\n\x1a\n") or
                         match[1] == "jpeg" and raw.startswith(b"\xff\xd8\xff") or
                         match[1] == "webp" and raw.startswith(b"RIFF") and raw[8:12] == b"WEBP")
                if not valid:
                    raise Problem("image_signature_mismatch")
            else:
                parsed = urlsplit(url)
                if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
                    raise Problem("invalid_image_url")
        else:
            raise Problem("unsupported_content_part")


def validate(request, config=None):
    config = config or DEFAULT_CONFIG
    fields(request, ("input", "questions"), ("model",))
    payload = {"model": config["model"], **request}
    if payload["model"] != "gpt-6-luna":
        raise Problem("unsupported_model")
    raw = encode(payload)
    if len(raw) > MAX_BYTES:
        raise Problem("input_too_large")
    evidence = payload["input"]
    if isinstance(evidence, str):
        text(evidence)
    elif isinstance(evidence, list) and 1 <= len(evidence) <= 64:
        for message in evidence:
            fields(message, ("role", "content"), ("type",))
            if not isinstance(message["role"], str) or message["role"] not in {"user", "developer", "system"} or message.get("type", "message") != "message":
                raise Problem("unsupported_message")
            content(message["content"], multimodal=message["role"] == "user")
    else:
        raise Problem("invalid_evidence")
    questions = payload["questions"]
    if not isinstance(questions, list) or not 1 <= len(questions) <= 400:
        raise Problem("invalid_questions")
    names = set()
    for question in questions:
        if not isinstance(question, dict):
            raise Problem("invalid_question")
        kind = question.get("type")
        if not isinstance(kind, str) or kind not in {"predicate", "choice", "score"}:
            raise Problem("invalid_question_type")
        extra = {"choice": ("choices",), "score": ("levels",)}.get(kind, ())
        fields(question, ("name", "type", "instructions", *extra))
        text(question["name"], 128)
        if question["name"] in names:
            raise Problem("duplicate_question_name")
        names.add(question["name"])
        content(question["instructions"])
        if kind == "predicate":
            continue
        values = question[extra[0]]
        if not isinstance(values, list) or not 2 <= len(values) <= (255 if kind == "choice" else 10):
            raise Problem("invalid_options")
        key = "value" if kind == "choice" else "label"
        seen = set()
        for option in values:
            fields(option, (key,), ("description",))
            value = option[key]
            if kind == "choice" and type(value) not in (str, bool) or kind == "score" and not isinstance(value, str):
                raise Problem("invalid_option")
            if isinstance(value, str):
                text(value)
            typed = (type(value).__name__, value)
            if typed in seen:
                raise Problem("duplicate_option")
            seen.add(typed)
            if "description" in option:
                text(option["description"])
    return payload


def preview(request, config=None):
    payload = validate(request, config)
    raw = encode(payload)
    return {"status": "validated", "online": False, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
            "questions": len(payload["questions"]), "model": payload["model"]}


def number(value, low, high):
    if type(value) not in (int, float) or not math.isfinite(value) or not low <= value <= high:
        raise Problem("invalid_response")


def validate_response(data, payload):
    if not isinstance(data, dict) or not isinstance(data.get("model"), str) or not isinstance(data.get("usage"), dict):
        raise Problem("invalid_response")
    answers = data.get("answers")
    if not isinstance(answers, list) or len(answers) != len(payload["questions"]):
        raise Problem("invalid_response")
    for question, answer in zip(payload["questions"], answers):
        if not isinstance(answer, dict) or answer.get("name") != question["name"]:
            raise Problem("invalid_response")
        if answer.get("type") == "refusal":
            continue
        kind = question["type"]
        if answer.get("type") != kind:
            raise Problem("invalid_response")
        if kind == "predicate":
            number(answer.get("probability"), 0, 1)
            continue
        number(answer.get("confidence"), 0, 1)
        key = "value" if kind == "choice" else "label"
        options = question["choices" if kind == "choice" else "levels"]
        expected = [(type(x[key]), x[key]) for x in options]
        probabilities = answer.get("probabilities")
        if not isinstance(probabilities, list) or len(probabilities) != len(options):
            raise Problem("invalid_response")
        found = []
        for index, row in enumerate(probabilities):
            if not isinstance(row, dict):
                raise Problem("invalid_response")
            number(row.get("probability"), 0, 1)
            found.append((type(row.get(key)), row.get(key)))
            if kind == "score" and (type(row.get("value")) is not int or row["value"] != index):
                raise Problem("invalid_response")
        if found != expected or abs(sum(x["probability"] for x in probabilities) - 1) > 0.001:
            raise Problem("invalid_response")
        if kind == "choice":
            if (type(answer.get("choice")), answer.get("choice")) not in expected:
                raise Problem("invalid_response")
        else:
            number(answer.get("score"), 0, len(options) - 1)
            weighted = sum(i * x["probability"] for i, x in enumerate(probabilities))
            if abs(answer["score"] - weighted) > 0.001:
                raise Problem("invalid_response")
    for key in ("input_tokens", "output_tokens", "total_tokens"):
        if type(data["usage"].get(key)) is not int or data["usage"][key] < 0:
            raise Problem("invalid_response")
    return data


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def evaluate(request, config, *, approved=False, opener=None):
    payload = validate(request, config)
    if approved is not True:
        return {"status": "approval_required", "online": False}
    credential = os.environ.get(config["credential_env"], "").strip()
    if not credential:
        return {"status": "needs_credentials", "credential_env": config["credential_env"], "online": False}
    if not credential.isascii() or any(c.isspace() for c in credential):
        return {"status": "invalid_credentials", "online": False}
    transport = opener or urllib.request.build_opener(NoRedirect())
    start = time.monotonic()
    req = urllib.request.Request(ENDPOINT, data=encode(payload), headers={"Authorization": "Bearer " + credential,
        "Content-Type": "application/json"}, method="POST")
    try:
        with transport.open(req, timeout=config["timeout_seconds"]) as response:
            raw = response.read(MAX_RESPONSE + 1)
            request_id = response.headers.get("x-request-id")
        if len(raw) > MAX_RESPONSE:
            raise Problem("response_too_large")
        data = validate_response(json.loads(raw), payload)
        refused = sum(answer["type"] == "refusal" for answer in data["answers"])
        result = {"status": "refused" if refused == len(data["answers"]) else "partial_refusal" if refused else "ok",
                  "provider": "openai", "response": data, "request_id": request_id}
    except urllib.error.HTTPError as exc:
        result = {"status": "http_error", "http_status": exc.code}
    except (urllib.error.URLError, TimeoutError, OSError):
        result = {"status": "transport_error"}
    except (ValueError, TypeError, RecursionError, UnicodeError):
        result = {"status": "invalid_response"}
    return {**result, "online": True, "attempts": 1, "latency_ms": round((time.monotonic() - start) * 1000)}
