import argparse
import json
import threading
from .core import Workspace, Previews, Problem


def main(argv=None):
    parser = argparse.ArgumentParser(description="Inspect a selected project or preview an explicit static file manifest")
    parser.add_argument("--root", required=True)
    parser.add_argument("command", choices=("inspect", "artifacts", "preview"))
    parser.add_argument("--files", nargs="+")
    parser.add_argument("--entry")
    args = parser.parse_args(argv)
    previews = None
    try:
        workspace = Workspace(args.root)
        if args.command == "inspect":
            result = workspace.inspect()
        elif args.command == "artifacts":
            result = workspace.artifacts(args.files)
        else:
            previews = Previews(workspace)
            result = previews.start(args.entry, args.files)
        print(json.dumps(result, ensure_ascii=False), flush=True)
        if previews:
            threading.Event().wait()
        return 0
    except KeyboardInterrupt:
        return 0
    except (Problem, OSError, ValueError, TypeError, AttributeError):
        print('{"status":"local_error"}', flush=True)
        return 1
    finally:
        if previews:
            previews.close()
