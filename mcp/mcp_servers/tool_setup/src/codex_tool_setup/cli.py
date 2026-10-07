"""Expose the maintained setup without requiring a repository checkout."""
import sys


def setup_main():
    args = sys.argv[1:]
    if not args or args[0] in {"--help", "-h", "--list"}:
        print("Usage: codex-setup CATEGORY [OPTIONS]\nCategories: agents, skills, plugins, mcp\nUse CATEGORY --list to select an item")
        return 0
    if args[0] in {"agents", "skills", "plugins"}:
        from ._setup.mcp.scripts.manage_categories import main as configure
        return configure(args)
    if args[0] == "mcp":
        from ._setup.mcp.scripts.install_development_tool import main as install
        forwarded = args[1:]
        if forwarded and not forwarded[0].startswith("-"):
            forwarded = ["--tool", forwarded[0], *forwarded[1:]]
        return install(["--guided", "--interface", "mcp", *forwarded])
    print("Unknown category; use --list", file=sys.stderr)
    return 2


def main():
    from ._setup.mcp.scripts.install_development_tool import main as install
    return install()


def mcp_main():
    from ._setup.mcp.scripts.install_development_tool import main as install
    args = sys.argv[1:]
    if args and not args[0].startswith("-"):
        args = ["--tool", args[0], *args[1:]]
    return install(["--guided", "--interface", "mcp", *args])


def check_main():
    from ._setup.mcp.scripts.check_development_tools import main as check
    return check()


def update_main():
    from ._setup.mcp.scripts.update_development_tool import main as update
    return update()


def uninstall_main():
    from ._setup.mcp.scripts.uninstall_mcp import main as uninstall
    args = sys.argv[1:]
    if args and not args[0].startswith("-"):
        args = ["--tool", args[0], *args[1:]]
    return uninstall(args or ["--guided"])
