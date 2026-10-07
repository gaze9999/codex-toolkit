"""Render only the managed Desktop preferences; never modify the user config."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import tomllib


PROMPT_KEYS = ("git-commit-instructions", "git-pr-instructions", "git-pr-watch-instructions")
FIELDS = {
    "features": {"memories": bool},
    "memories": {"generate_memories": bool, "use_memories": bool, "disable_on_external_context": bool},
    "desktop": {"git-branch-prefix": str},
}


def render(source: Path) -> str:
    data = tomllib.loads((source / "desktop-preferences.toml").read_text(encoding="utf-8"))
    if set(data) != set(FIELDS):
        raise ValueError("Unexpected or missing preference section")
    for section, fields in FIELDS.items():
        if set(data[section]) != set(fields):
            raise ValueError(f"Unexpected or missing key in {section}")
        for key, expected in fields.items():
            if type(data[section][key]) is not expected:
                raise ValueError(f"Invalid type for {section}.{key}")
    prompts = tomllib.loads((source / "git-instructions.toml").read_text(encoding="utf-8"))
    if set(prompts) != {"desktop"} or set(prompts["desktop"]) != set(PROMPT_KEYS):
        raise ValueError("Unexpected or missing Git instruction key")
    for key in PROMPT_KEYS:
        prompt = prompts["desktop"][key]
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError(f"Empty or invalid Git instruction: {key}")
        prompt = prompt.strip()
        data["desktop"][key] = prompt + "\n"
    lines = ["# Selected settings only. Merge existing tables; do not replace the whole config."]
    for section, values in data.items():
        lines.extend(["", f"[{section}]"])
        lines.extend(f"{key} = {json.dumps(value, ensure_ascii=False)}" for key, value in values.items())
    result = "\n".join(lines) + "\n"
    if tomllib.loads(result) != data:
        raise ValueError("TOML round-trip mismatch")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Create a UTF-8 fragment; refuses an existing file")
    args = parser.parse_args()
    try:
        result = render(Path(__file__).resolve().parents[2] / "agents")
        if args.output:
            with args.output.open("x", encoding="utf-8", newline="\n") as stream:
                stream.write(result)
        else:
            sys.stdout.reconfigure(encoding="utf-8")
            print(result, end="")
    except (OSError, ValueError) as error:
        parser.exit(1, f"Settings rendering failed: {error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
