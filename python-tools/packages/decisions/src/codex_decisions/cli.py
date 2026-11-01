"""Human CLI for the same core used by MCP."""
import argparse
import json
from pathlib import Path
from . import core


def main(argv=None):
    parser = argparse.ArgumentParser(description="Bounded OpenAI Decisions evaluation; no automatic credential creation")
    parser.add_argument("--config", type=Path, help="Optional JSON with model, credential_env and timeout_seconds; no secret values")
    parser.add_argument("command", choices=("status", "validate", "evaluate"))
    parser.add_argument("--input", type=Path, help="UTF-8 request JSON")
    parser.add_argument("--approved", action="store_true", help="Explicitly authorize this evidence/rubric transfer and paid request")
    args = parser.parse_args(argv)
    try:
        config = core.config_from(args.config)
        if args.command == "status":
            result = core.status(config)
        else:
            if args.input is None:
                parser.error("--input is required")
            request = core.read_json(args.input)
            result = core.preview(request, config) if args.command == "validate" else core.evaluate(request, config, approved=args.approved)
    except core.Problem as exc:
        result = {"status": "invalid_input", "reason": str(exc)}
    except OSError:
        result = {"status": "local_error"}
    print(json.dumps(result, ensure_ascii=False, allow_nan=False))
    return 0 if result["status"] in {"configured", "validated", "ok", "partial_refusal", "refused"} else 1
