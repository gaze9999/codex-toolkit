#!/usr/bin/env python3
"""Count exact BPE tokens locally for UTF-8 files, inline text or stdin."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from shared.runtime import resource_root


DEFAULT_ENCODING = "o200k_base"


def count_text(text: str, encoding_name: str = DEFAULT_ENCODING) -> dict[str, object]:
    """Count literal text, including strings that look like special tokens.

    Counts exclude message framing, tool definitions and other request content.
    Missing dependencies, encoding errors and cache/download failures propagate.
    """
    import tiktoken

    encoding = tiktoken.get_encoding(encoding_name)
    tokens = len(encoding.encode_ordinary(text))
    return {
        "encoding": encoding.name,
        "method": "tiktoken",
        "chars": len(text),
        "tokens": tokens,
        "utf8_bytes": len(text.encode("utf-8")),
        "chars_per_token": len(text) / tokens if tokens else None,
    }


def count_file(path: Path, encoding_name: str = DEFAULT_ENCODING) -> dict[str, object]:
    """Read UTF-8 with optional BOM, preserving CRLF and all other whitespace."""
    text = path.read_bytes().decode("utf-8-sig")
    return {"source": str(path), **count_text(text, encoding_name)}


def format_report(results: list[dict[str, object]]) -> str:
    lines = []
    for result in results:
        ratio = result["chars_per_token"]
        lines.extend([
            f"來源: {result['source']}",
            f"編碼: {result['encoding']}",
            f"字元數: {result['chars']:,}",
            f"Token 數: {result['tokens']:,}",
            f"UTF-8 bytes: {result['utf8_bytes']:,}",
            f"字元/Token: {ratio:.2f}" if ratio is not None else "字元/Token: 無 (空文字)",
            "",
        ])
    if len(results) > 1:
        lines.append(f"Token 總數 (各來源分別計算後加總): {sum(result['tokens'] for result in results):,}")
    return "\n".join(lines).rstrip() + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="本機精確計算 Token, 預設 o200k_base")
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--input", type=Path, nargs="+", help="一個或多個 UTF-8 文字檔")
    source.add_argument("--text", help="直接提供要計算的文字")
    parser.add_argument("--encoding", default=DEFAULT_ENCODING, help="tiktoken 編碼名稱 (預設 o200k_base)")
    parser.add_argument("--json", action="store_true", help="輸出 JSON")
    parser.add_argument("--html", type=Path, help="另存離線彩色 Token 檢視 HTML")
    parser.add_argument("--max-display-tokens", type=int, default=2000, help="每個來源的彩色顯示上限 (預設 2000)")
    parser.add_argument("--output", type=Path, help="另存結果, 使用 --json 或 .json 副檔名時儲存 JSON")
    args = parser.parse_args(argv)

    try:
        os.environ.setdefault("TIKTOKEN_CACHE_DIR", str(resource_root() / "tiktoken-cache"))
        if args.max_display_tokens < 1:
            raise ValueError("顯示 Token 數需大於 0")
        if args.html is not None:
            if not args.html.parent.is_dir():
                raise ValueError(f"HTML 輸出目錄不存在: {args.html.parent}")
            if args.html.exists() or args.html.is_symlink():
                raise ValueError(f"輸出檔已存在, 請使用新檔名: {args.html}")
            if args.output and args.html.resolve() == args.output.resolve():
                raise ValueError("HTML 與統計輸出需使用不同路徑")
        if args.output is not None:
            if args.output.exists() or args.output.is_symlink():
                raise ValueError(f"輸出檔已存在, 請使用新檔名: {args.output}")
            if args.input and any(args.output.resolve() == path.resolve() for path in args.input):
                raise ValueError("輸出路徑不可與來源檔相同")

        if args.input:
            documents = [(str(path), path.read_bytes().decode("utf-8-sig")) for path in args.input]
        elif args.text is not None:
            documents = [("inline", args.text)]
        elif sys.stdin.isatty():
            raise ValueError("請提供 --input、--text 或透過 stdin 傳入文字")
        else:
            # Prevent TextIOWrapper from normalizing CRLF or replacing Unicode.
            if hasattr(sys.stdin, "reconfigure"):
                sys.stdin.reconfigure(encoding="utf-8", errors="strict", newline="")
            documents = [("stdin", sys.stdin.read())]

        results = [{"source": source, **count_text(text, args.encoding)} for source, text in documents]
        html_report = None
        if args.html:
            from text.token_html import render_html

            html_report = render_html(documents, args.encoding, args.max_display_tokens)

        use_json = args.json or (args.output is not None and args.output.suffix.lower() == ".json")
        if use_json:
            report = json.dumps({
                "results": results,
                "total_tokens": sum(result["tokens"] for result in results),
            }, ensure_ascii=False, indent=2) + "\n"
        else:
            report = format_report(results)

        if args.output is not None:
            # Exclusive creation also guards an output appearing during counting.
            with args.output.open("x", encoding="utf-8", newline="\n") as stream:
                stream.write(report)
        if args.html:
            with args.html.open("x", encoding="utf-8", newline="\n") as stream:
                stream.write(html_report)
        print(report, end="")
        return 0
    except ImportError as exc:
        print(f'錯誤: 缺少相依套件 {exc.name or str(exc)}, 請使用執行此工具的 Python 安裝: python -m pip install "tiktoken>=0.7,<1" "regex>=2022.1.18"', file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"錯誤: {exc}", file=sys.stderr)
        print("計數或匯出失敗, 請確認來源、輸出路徑、編碼及 tiktoken 編碼快取可用", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
