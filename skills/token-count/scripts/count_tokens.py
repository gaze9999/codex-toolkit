#!/usr/bin/env python3
"""Run the canonical or Plugin-bundled Token Count core without duplicating it."""
from __future__ import annotations

import os
from pathlib import Path
import sys
import tempfile


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if stream is not None and hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    package_root = Path(__file__).resolve().parents[3]
    candidates = (
        package_root / "resources" / "token-count" / "src",
        package_root / "python-tools" / "src",
    )
    source = next((root for root in candidates
                   if (root / "text" / "token_count.py").is_file()
                   and (root / "shared" / "runtime.py").is_file()), None)
    if source is None:
        print("錯誤: 缺少 Token Count 核心, 請使用完整的文件與規格處理 Plugin 或 Toolkit checkout", file=sys.stderr)
        return 2

    # Keep generated/installed payloads unchanged during ordinary execution.
    sys.dont_write_bytecode = True
    os.environ.setdefault("TIKTOKEN_CACHE_DIR", os.environ.get(
        "DATA_GYM_CACHE_DIR", str(Path(tempfile.gettempdir()) / "data-gym-cache"),
    ))
    sys.path.insert(0, str(source))
    if sys.argv[1:2] == ["context"]:
        from text.context_budget import main as budget_main

        return budget_main(sys.argv[2:])
    from text.token_count import main as count_main

    return count_main()


if __name__ == "__main__":
    raise SystemExit(main())
