"""Run with a built executable. All mutations are confined to a new fixture."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

exe = Path(sys.argv[1]).resolve(strict=True)
base = Path(tempfile.mkdtemp(prefix="artifact-audit-")).resolve()
repo = base / "projects" / "同名 project"
linked = base / "external" / repo.name
homes = [base / "codex", base / "claude"]
repo.mkdir(parents=True)
for folder in homes:
    folder.mkdir()
env = {**os.environ, "LOCALAPPDATA": str(base / "state"), "HOME": str(base), "CODEX_HOME": str(homes[0]), "CLAUDE_CONFIG_DIR": str(homes[1])}


def git(*args):
    subprocess.run(["git", "-C", str(repo), *map(str, args)], env=env, check=True, capture_output=True)


def cli(*args, code=0):
    result = subprocess.run([str(exe), *map(str, args)], env=env, capture_output=True, text=True, encoding="utf-8")
    assert result.returncode == code, (result.stdout, result.stderr)
    return json.loads(result.stdout) if result.stdout else None


git("init")
(repo / ".gitignore").write_text("__pycache__/\n", encoding="utf-8")
(repo / "demo.py").touch()
git("add", ".gitignore", "demo.py")
git("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-m", "fixture")
git("worktree", "add", "-b", "fixture", linked)
for tree in [repo, linked]:
    cache = tree / "__pycache__"
    cache.mkdir()
    (cache / "demo.cpython-313.pyc").write_bytes(b"abc")
(homes[0] / "session.backup").write_bytes(b"opaque")
reports = base / "reports"
args = ["scan", "--workspace", repo.parent, "--workspace", repo, "--out", reports]
scanned = cli(*args)
doc = json.loads(Path(scanned["json"]).read_bytes())
rows = doc["items"]
allowed = [r for r in rows if r["selectable"]]
assert len(allowed) == 2 and len({r["project"] for r in allowed}) == 1, rows
assert any(r["status"] == "受保護" for r in rows)
assert Path(scanned["html"]).is_file()


def apply(scan, rows, code):
    selection = base / "selection.json"
    selection.write_text(json.dumps({"batch": scan["batch"], "ids": [r["id"] for r in rows]}), encoding="utf-8")
    return cli("apply", "--report", scan["json"], "--selection", selection, "--out", reports, code=code)


changed = Path(allowed[0]["path"]) / "new.txt"
changed.touch()
result = apply(scanned, allowed, 1)
assert result["counts"] == {"skipped": 1, "deleted": 1}, result
assert changed.is_file() and not Path(allowed[1]["path"]).exists()
assert result["deleted_bytes"] == 3
assert apply(scanned, allowed, 2) is None
# Recreate an interrupted result in an isolated copy of its execution journal.
partial = base / "interrupted"
partial.mkdir()
run = Path(result["run"])
(partial / "plan.json").write_bytes((run / "plan.json").read_bytes())
events = (run / "events.jsonl").read_bytes().splitlines(keepends=True)
cut = next(i for i, event in enumerate(events) if json.loads(event)["status"] == "started")
(partial / "events.jsonl").write_bytes(b"".join(events[:cut + 1]) + b'{"torn"')
recovered = cli("report", "--run", partial, code=1)
assert recovered["counts"]["unknown"] >= 1
older, newer = [homes[0] / "backups/codex-setup" / stamp / "AGENTS.md" for stamp in ["20261001T010101000000Z","20261002T010101000000Z"]]
for backup in [older,newer]:
    backup.parent.mkdir(parents=True)
    backup.write_bytes(b"test backup")
(homes[0] / "AGENTS.md").touch()
rotation = cli(*args)
backups = [r for r in json.loads(Path(rotation["json"]).read_bytes())["items"] if r["rule"]=="setup-rotation"]
assert len(backups)==2 and sum(r["selectable"] for r in backups)==1
assert apply(rotation,[r for r in backups if r["selectable"]],0)["counts"]=={"deleted":1}
assert newer.is_file() and not older.exists()
empty=base/"empty"
empty.mkdir()
empty_scan=cli("scan","--workspace",empty,"--codex-home",empty,"--claude-home",empty,"--out",reports)
assert empty_scan["count"]==0 and not empty_scan["partial"]
assert cli("scan", "--workspace", base / "missing", "--out", reports, code=1)["gaps"]
# A newly tracked member invalidates the earlier eligibility decision.
changed.unlink()
fresh = cli(*args)
fresh_rows = json.loads(Path(fresh["json"]).read_bytes())["items"]
candidate = next(r for r in fresh_rows if r["selectable"])
git_tree = Path(candidate["tree"])
subprocess.run(["git","-C",str(git_tree),"add","-f","__pycache__/demo.cpython-313.pyc"],env=env,check=True)
assert apply(fresh,[candidate],1)["counts"] == {"skipped":1}
# Local stdio discovery, scan and read-only recovery use the same executable.
calls = [{"method":"initialize","params":{"protocolVersion":"2025-06-18"}},{"method":"tools/list"},
         {"method":"tools/call","params":{"name":"scan_artifacts","arguments":{"workspace":[str(repo)],"out":str(reports)}}},
         {"method":"tools/call","params":{"name":"report_artifacts","arguments":{"run":str(partial)}}}]
wire = "".join(json.dumps({"jsonrpc":"2.0","id":i,**call})+"\n" for i,call in enumerate(calls))
r = subprocess.run([str(exe),"mcp"],input=wire,env=env,text=True,encoding="utf-8",capture_output=True,check=True)
responses = [json.loads(line)["result"] for line in r.stdout.splitlines()]
assert len(responses[1]["tools"]) == 3 and all(not v["isError"] for v in responses[2:])
# Exercise selection validity and permanent deletion over the stdio entry as well.
older.write_bytes(b"second rotation")
again=cli(*args)
items=json.loads(Path(again["json"]).read_bytes())["items"]
old=next(r for r in items if r["rule"]=="setup-rotation" and r["selectable"])
selection=base/"mcp-selection.json"
selection.write_text(json.dumps({"batch":again["batch"],"ids":[old["id"]]}),encoding="utf-8")
call={"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"apply_artifacts","arguments":{"report":again["json"],"selection":str(selection),"out":str(reports)}}}
reply=subprocess.run([str(exe),"mcp"],input=json.dumps(call)+"\n",env=env,text=True,encoding="utf-8",capture_output=True,check=True)
result_data=json.loads(reply.stdout)["result"]
assert not result_data["isError"] and json.loads(result_data["content"][0]["text"])["counts"]=={"deleted":1}
assert not older.exists() and newer.is_file()
# Preserve a file substituted since the scan, even with equal length and mtime.
older.write_bytes(b"original")
swap=cli(*args)
old=next(r for r in json.loads(Path(swap["json"]).read_bytes())["items"] if r["rule"]=="setup-rotation" and r["selectable"])
mtime=older.stat().st_mtime_ns
older.rename(older.with_suffix(".original"))
older.write_bytes(b"replaced")
os.utime(older,ns=(mtime,mtime))
assert apply(swap,[old],1)["counts"]=={"skipped":1} and older.read_bytes()==b"replaced"
# Redirect a scanned parent to a separate directory, then ensure its contents survive.
redirect=cli(*args)
row=next(r for r in json.loads(Path(redirect["json"]).read_bytes())["items"] if r["rule"]=="setup-rotation" and r["selectable"])
target=base/"redirected"
older.parent.rename(target)
if os.name=="nt":
    import _winapi
    _winapi.CreateJunction(str(target),str(older.parent))
else:
    older.parent.symlink_to(target,target_is_directory=True)
assert apply(redirect,[row],1)["counts"]=={"skipped":1}
assert (target/older.name).read_bytes()==b"replaced"
# A busy member survives, its sibling can be removed, and the directory stays.
busy=repo/"busy"
cache=busy/"__pycache__"
cache.mkdir(parents=True)
for stem in ("free","held"):
    (busy/(stem+".py")).touch()
    (cache/(stem+".cpython-313.pyc")).write_bytes(b"cache")
busy_scan=cli(*args)
busy_row=next(r for r in json.loads(Path(busy_scan["json"]).read_bytes())["items"] if Path(r["path"])==cache)
with (cache/"held.cpython-313.pyc").open("rb"):
    partial_result=apply(busy_scan,[busy_row],1)
assert partial_result["counts"]=={"partial":1} and partial_result["deleted_bytes"]==5
assert (cache/"held.cpython-313.pyc").exists() and not (cache/"free.cpython-313.pyc").exists()
print(json.dumps({"fixture":str(base),"html":scanned["html"],"changes":result["html"],"counts":result["counts"]}))

