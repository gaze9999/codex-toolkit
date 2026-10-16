#!/usr/bin/env python3
"""Estimate instruction, Skill and tool context from selected local sources."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import sys

from shared.runtime import resource_root
from text.token_count import count_text


PROFILE = Path(__file__).with_name("context_estimates.json")


def read_config(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        import tomllib
    except ImportError as exc:
        raise ValueError("環境探索需要 Python 3.11+") from exc
    return tomllib.loads(path.read_text(encoding="utf-8-sig"))


def first_instruction(folder: Path, fallbacks: list[str] = ()) -> Path | None:
    for name in ("AGENTS.override.md", "AGENTS.md", *fallbacks):
        if Path(name).name != name:
            raise ValueError("指示檔 fallback 必須是檔名")
        path = folder / name
        if path.is_file() and path.read_bytes().strip():
            return path
    return None


def project_chain(project: Path, fallbacks: list[str]) -> list[Path]:
    folders = []
    for folder in (project, *project.parents):
        folders.append(folder)
        if (folder / ".git").exists():
            break
    else:
        folders = [project]
    return [path for folder in reversed(folders)
            if (path := first_instruction(folder, fallbacks)) is not None]


def skill_metadata(path: Path) -> str:
    text = path.read_text(encoding="utf-8-sig")
    match = re.match(r"\A---\r?\n(.*?)\r?\n---", text, re.S)
    if not match:
        raise ValueError(f"Skill 缺少 frontmatter: {path}")
    fields = {}
    lines = match.group(1).splitlines()
    for index, line in enumerate(lines):
        match = re.match(r"^(name|description):\s*(.*)$", line)
        if match:
            key, value = match.groups()
            if value in (">", ">-", "|", "|-"):
                continuation = []
                for following in lines[index + 1:]:
                    if following and not following[0].isspace():
                        break
                    continuation.append(following.strip())
                value = " ".join(continuation)
            fields[key] = value.strip("\"'")
    if not fields.get("name") or not fields.get("description"):
        raise ValueError(f"Skill 缺少名稱或說明: {path}")
    return f"- {fields['name']}: {fields['description']} (file: {path})"


def discover_skills(home: Path, project: Path, config: dict, extra_roots: list[Path]) -> list[Path]:
    roots = [home / "skills", home.parent / ".agents" / "skills", project / ".agents" / "skills", *extra_roots]
    skill_settings = {os.path.normcase(str(Path(row["path"]).resolve())): row.get("enabled", True)
                      for row in config.get("skills", {}).get("config", [])}
    disabled = {path for path, enabled in skill_settings.items() if enabled is False}
    plugins = config.get("plugins", {})
    cache = home / "plugins" / "cache"
    if cache.is_dir():
        for market in sorted(cache.iterdir()):
            if not market.is_dir():
                continue
            for plugin in sorted(market.iterdir()):
                if not plugin.is_dir() or plugins.get(f"{plugin.name}@{market.name}", {}).get("enabled") is False:
                    continue
                versions = [p for p in plugin.iterdir() if p.is_dir() and re.fullmatch(r"\d+(?:\.\d+)+(?:[-+][\w.-]+)?", p.name)]
                if versions:
                    latest = max(versions, key=lambda p: tuple(int(x) for x in re.findall(r"\d+", p.name)))
                    roots.append(latest / "skills")
    paths = {}
    for root in roots:
        for path in sorted(root.glob("*/SKILL.md")) + sorted((root / ".system").glob("*/SKILL.md")):
            key = os.path.normcase(str(path.resolve()))
            if key not in disabled:
                paths[key] = path
    return list(paths.values())


def estimate_context(project: Path, home: Path, *, encoding: str = "o200k_base",
                     instructions: list[Path] = (), active_skills: list[Path] = (),
                     active_roles: list[Path] = (),
                     skill_roots: list[Path] = (), tool_schemas: list[Path] = (),
                     contents: list[Path] = (), builtin_tools: int = 10, mcp_tools: int = 0,
                     profile_path: Path = PROFILE) -> dict:
    project, home = project.resolve(), home.resolve()
    if not project.is_dir():
        raise ValueError(f"專案目錄不存在: {project}")
    if builtin_tools < 0 or mcp_tools < 0:
        raise ValueError("工具數量需大於等於 0")
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    for field in ("system_tokens", "builtin_tool_tokens"):
        if type(profile.get(field)) is not int or profile[field] < 0:
            raise ValueError(f"預估設定無效: {field}")
    for field in ("mcp_server_tokens", "mcp_tool_tokens"):
        pair = profile.get(field)
        if not isinstance(pair, list) or len(pair) != 2 or any(type(x) is not int or x < 0 for x in pair) or pair[0] > pair[1]:
            raise ValueError(f"預估設定無效: {field}")
    config = read_config(home / "config.toml")
    git_root = next((folder for folder in (project, *project.parents) if (folder / ".git").exists()), project)
    project_config = read_config(git_root / ".codex" / "config.toml")
    for field in ("mcp_servers", "plugins"):
        config[field] = {**config.get(field, {}), **project_config.get(field, {})}
    config["skills"] = {"config": config.get("skills", {}).get("config", []) + project_config.get("skills", {}).get("config", [])}
    for field in ("project_doc_max_bytes", "project_doc_fallback_filenames"):
        if field in project_config:
            config[field] = project_config[field]
    byte_budget = config.get("project_doc_max_bytes", 32768)
    if type(byte_budget) is not int or byte_budget < 0:
        raise ValueError("project_doc_max_bytes 需大於等於 0")
    rows, seen = [], set()

    def add_text(category: str, text: str, sources: list[str], method: str = "file_bpe"):
        tokens = count_text(text, encoding)["tokens"]
        rows.append({"category": category, "low": tokens, "high": tokens, "method": method,
                     "sources": sources})

    def add_files(category: str, paths: list[Path], initial: bool = False):
        nonlocal byte_budget
        texts, sources = [], []
        for path in paths:
            key = os.path.normcase(str(path.resolve()))
            if key in seen:
                continue
            seen.add(key)
            text = path.read_bytes().decode("utf-8-sig")
            if initial:
                raw = text.encode("utf-8")[:byte_budget]
                text = raw.decode("utf-8", errors="ignore")
                byte_budget -= len(text.encode("utf-8"))
            texts.append(text)
            sources.append(str(path))
        if sources:
            add_text(category, "\n\n".join(texts), sources)

    global_file = first_instruction(home)
    add_files("Global Agent", [global_file] if global_file else [], initial=True)
    add_files("Project Agent", project_chain(project, config.get("project_doc_fallback_filenames", [])), initial=True)
    add_files("其他指示與參考", instructions)
    skills = discover_skills(home, git_root, config, skill_roots)
    if skills:
        add_text("Skills 探索清單", "\n".join(skill_metadata(path) for path in skills),
                 [str(path) for path in skills], "catalog_render_bpe")
    add_files("啟用的 Skills", active_skills)
    add_files("啟用的角色", active_roles)
    memory = home / "memories" / "memory_summary.md"
    if memory.is_file():
        add_files("Memory 摘要", [memory])
    roles = {}
    role_sources = []
    for cfg_path, cfg in ((home / "config.toml", config), (git_root / ".codex" / "config.toml", project_config)):
        for name, value in cfg.get("agents", {}).items():
            if isinstance(value, dict) and value.get("description"):
                roles[name] = value["description"]
                role_sources.append(str(cfg_path))
    if roles:
        add_text("角色探索清單", "\n".join(f"- {name}: {desc}" for name, desc in sorted(roles.items())),
                 sorted(set(role_sources)), "catalog_render_bpe")
    add_files("任務文字與文件", contents)
    servers = [name for name, value in config.get("mcp_servers", {}).items() if value.get("enabled", True)]
    rows.append({"category": "系統基礎預估", "low": profile["system_tokens"], "high": profile["system_tokens"],
                 "method": "community_estimate", "sources": [profile["sources"][0]["url"]]})
    if tool_schemas:
        add_files("選定工具定義", tool_schemas)
    elif builtin_tools:
        rows.append({"category": f"內建工具預估 ({builtin_tools} 項)",
                     "low": builtin_tools * profile["builtin_tool_tokens"],
                     "high": builtin_tools * profile["builtin_tool_tokens"], "method": "community_estimate",
                     "sources": [profile["sources"][1]["url"]]})
    if servers:
        rows.append({"category": f"MCP Server 預估 ({len(servers)} 個)",
                     "low": len(servers) * profile["mcp_server_tokens"][0],
                     "high": len(servers) * profile["mcp_server_tokens"][1], "method": "community_estimate",
                     "sources": [profile["sources"][1]["url"]]})
    if mcp_tools and not tool_schemas:
        rows.append({"category": f"MCP 工具預估 ({mcp_tools} 項)",
                     "low": mcp_tools * profile["mcp_tool_tokens"][0],
                     "high": mcp_tools * profile["mcp_tool_tokens"][1], "method": "community_estimate",
                     "sources": [profile["sources"][2]["url"]]})
    return {"encoding": encoding, "project": str(project), "profile_checked_on": profile["checked_on"],
            "skill_count": len(skills), "mcp_servers": servers, "components": rows,
            "total": {"low": sum(row["low"] for row in rows), "high": sum(row["high"] for row in rows)},
            "sources": profile["sources"] + [{"url": url} for url in profile["official_sources"]]}


def format_budget(report: dict) -> str:
    def value(low, high):
        return f"{low:,}" if low == high else f"{low:,}–{high:,}"
    lines = [f"編碼: {report['encoding']}", f"來源日期: {report['profile_checked_on']}", "", "| 項目 | Token |", "|---|---:|"]
    lines += [f"| {row['category']} | {value(row['low'], row['high'])} |" for row in report["components"]]
    lines += [f"| 預估總計 | {value(**report['total'])} |", "", "來源:"]
    for row in report["components"]:
        sources = row["sources"]
        label = (f"{len(sources)} 份 SKILL.md metadata" if row["category"] == "Skills 探索清單" and len(sources) > 3
                 else "、".join(sources))
        lines.append(f"- {row['category']}: {label}")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="預估 Global、Project Agent、Skills 與工具的 Token")
    parser.add_argument("--project", type=Path, default=Path.cwd())
    parser.add_argument("--codex-home", type=Path, default=Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")))
    for flag in ("instruction", "active-skill", "active-role", "skill-root", "tool-schema", "content"):
        parser.add_argument(f"--{flag}", type=Path, action="append", default=[])
    parser.add_argument("--builtin-tools", type=int, default=10, help="未提供工具定義時的內建工具情境數量")
    parser.add_argument("--mcp-tools", type=int, default=0, help="未提供工具定義時的 MCP 工具情境數量")
    parser.add_argument("--encoding", default="o200k_base")
    parser.add_argument("--profile", type=Path, default=PROFILE)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.output is not None and (args.output.exists() or args.output.is_symlink()):
            raise ValueError(f"輸出檔已存在: {args.output}")
        os.environ.setdefault("TIKTOKEN_CACHE_DIR", str(resource_root() / "tiktoken-cache"))
        report = estimate_context(args.project, args.codex_home, encoding=args.encoding,
                                  instructions=args.instruction, active_skills=args.active_skill,
                                  active_roles=args.active_role,
                                  skill_roots=args.skill_root, tool_schemas=args.tool_schema, contents=args.content,
                                  builtin_tools=args.builtin_tools, mcp_tools=args.mcp_tools, profile_path=args.profile)
        rendered = (json.dumps(report, ensure_ascii=False, indent=2) + "\n") if args.json or (
            args.output and args.output.suffix.lower() == ".json") else format_budget(report)
        if args.output:
            with args.output.open("x", encoding="utf-8", newline="\n") as stream:
                stream.write(rendered)
        print(rendered, end="")
        return 0
    except Exception as exc:
        print(f"錯誤: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
