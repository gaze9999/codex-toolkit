# Jev MCP and Skill package

One API client supplies MCP tools and CLI commands across projects. The Skill governs optional use, required context and approved data-transfer boundaries.

Requires Python 3.10+ and network access for initial installation. Windows, macOS and Linux share source; installation creates a platform-specific isolated runtime with the pinned official MCP SDK.

Installing the Skill or Plugin alone does not install Python dependencies. Use the baseline bundle or the standalone installer below on each computer; keep its isolated runtime rather than installing MCP into an unrelated system Python.

## Wheel and offline verification

The `codex-jev-mcp` wheel shares this client. From any directory, start an installed server with `python -I -B -m codex_jev_mcp.mcp_server`; `jev-verify` checks the offline protocol without calling the paid API.

The Toolkit baseline bundle provides default paths and runtime reuse through `launch-cli.cmd bootstrap --apply` or `sh launch-cli.sh bootstrap --apply`. The bundle must contain the preset's wheel; do not claim unpublished wheels are available in a latest release.

Local usage recording is off by default. Enable it through the separate `local-activity-monitor` only when requested; see [opt-in monitoring](references/usage.md#opt-in-local-monitoring).

## Skill ZIP installation

Extract the complete folder and open a terminal beside `jev-evaluation/`. Skip key setup when the machine already has usable credentials.

Windows:

```powershell
python -B jev-evaluation/scripts/jev.py setup-key
python -B jev-evaluation/scripts/install_mcp.py --verify-online
```

macOS/Linux:

```sh
python3 -B jev-evaluation/scripts/jev.py setup-key
python3 -B jev-evaluation/scripts/install_mcp.py --verify-online
```

`setup-key` hides input and writes a plaintext credential file in the personal Codex credentials directory, with mode 0600 on macOS/Linux. Existing `TYPESAFE_API_KEY` is also supported; keys never belong in the Skill or ZIP.

The installer checks the pinned SDK's imports before registration, even when a requirements cache marker exists. It reinstalls broken dependencies only inside the selected runtime and reports its `python` path. Run `scripts/verify_mcp.py` with that interpreter; `--help` works without the SDK, while an actual check reports `mcp_sdk_missing` when the chosen interpreter lacks it. Do not copy virtual environments between devices.

Reload Codex and inspect `jev_rank`, `jev_evaluate` and `jev_status` under the `jev` server. Installation preserves unrelated configuration, backs up changed files and verifies a real MCP call with public input when online verification is requested.

Use `--replace` for an authorized replacement or `--dry-run` to preview paths without packages, writes or connections:

```sh
python3 -B jev-evaluation/scripts/install_mcp.py --replace --verify-online
```

Reuse an existing `.codex/skills/jev-evaluation` location. New installations default to `~/.agents/skills`; `CODEX_HOME` or `--skill-root` may select a verified location. Avoid duplicate installations.

## Use and maintenance

- User-level MCP registration can serve multiple projects; project `AGENTS.md` retains only local boundaries.
- Tools receive explicitly supplied candidate summaries or finite questions, without scanning repositories or conversation history.
- Main retains required context. `required` candidates keep their IDs, are not sent to Jev and are not removed by ranking.
- The server uses existing environment/file credentials; tool arguments contain no key. API failures return fallback and Main continues the established workflow.
- Source is portable; each device builds its own runtime/config paths. Rerun the installer after moving it, preserving the existing key.

See [usage.md](references/usage.md) for input, diagnosis and synchronization. Report actual platform/Apple Silicon verification rather than inferring runtime compatibility from Python syntax.

## ChatGPT on iPhone/iPad

This package supplies local stdio MCP on Windows/macOS/Linux. Signing into the same account does not connect a mobile client to a desktop process.

For mobile access, verify current client support, account permissions and transport. Remote integration needs an HTTPS endpoint and authentication; this package does not deploy that service automatically.

Sources: [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk), [Codex MCP configuration](https://learn.chatgpt.com/docs/extend/mcp?surface=cli), [ChatGPT app restrictions](https://help.openai.com/en/articles/12584461-developer-mode-and-full-mcp-apps-in-chatgpt-beta).
