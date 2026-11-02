import asyncio
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path
import unittest
import urllib.error
import urllib.request
from mcp import Client
from mcp.client.stdio import StdioServerParameters


class ProtocolTests(unittest.IsolatedAsyncioTestCase):
    async def test_owned_preview_through_stdio(self):
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / "index.html").write_text("<h1>Protocol fixture</h1>", encoding="utf-8")
            parameters = StdioServerParameters(command=sys.executable, args=["-m", "codex_visual_runtime.server"], env=os.environ.copy())
            async with Client(parameters, read_timeout_seconds=20) as client:
                tools = (await client.list_tools()).tools
                names = sorted(tool.name for tool in tools)
                self.assertEqual(names, ["visual_artifacts", "visual_inspect", "visual_preview_start", "visual_preview_status", "visual_preview_stop"])
                for tool in tools:
                    self.assertEqual("root" in tool.input_schema.get("required", []), tool.name in {"visual_inspect", "visual_artifacts", "visual_preview_start"})
                result = await client.call_tool("visual_inspect", {"root": directory})
                self.assertEqual(result.structured_content["status"], "ok")
                result = await client.call_tool("visual_artifacts", {"root": directory, "paths": ["index.html"]})
                self.assertEqual(result.structured_content["artifacts"][0]["bytes"], 25)
                result = await client.call_tool("visual_preview_start", {"root": directory, "entry": "index.html", "files": ["index.html"]})
                job = result.structured_content
                self.assertEqual(job["status"], "ready")
                with urllib.request.urlopen(job["url"]) as response:
                    self.assertIn(b"Protocol fixture", response.read())
                result = await client.call_tool("visual_preview_status", {"job_id": job["job_id"]})
                self.assertEqual(result.structured_content["status"], "ready")
                result = await client.call_tool("visual_preview_stop", {"job_id": job["job_id"]})
                self.assertEqual(result.structured_content["status"], "stopped")

    async def test_missing_blank_and_invalid_roots(self):
        with tempfile.TemporaryDirectory() as directory:
            parameters = StdioServerParameters(command=sys.executable, args=["-m", "codex_visual_runtime.server"], env=os.environ.copy())
            async with Client(parameters, read_timeout_seconds=20) as client:
                for name, arguments in (("visual_inspect", {}), ("visual_artifacts", {"paths": ["index.html"]}), ("visual_preview_start", {"entry": "index.html", "files": ["index.html"]})):
                    with self.subTest(tool=name):
                        result = await client.call_tool(name, arguments)
                        self.assertTrue(result.is_error)
                        result = await client.call_tool(name, {**arguments, "root": ""})
                        self.assertEqual(result.structured_content["status"], "local_error")
                for root in (str(Path(directory) / "missing"), str(Path(directory) / "file.txt")):
                    if root.endswith("file.txt"):
                        Path(root).write_text("fixture", encoding="utf-8")
                    result = await client.call_tool("visual_inspect", {"root": root})
                    self.assertEqual(result.structured_content["status"], "local_error")

    async def test_multiple_roots_share_only_owned_job_lifecycle(self):
        with tempfile.TemporaryDirectory() as directory:
            left, right = Path(directory) / "left", Path(directory) / "右側 project"
            for root, dependency, content in ((left, "react", b"<h1>Left</h1>"), (right, "vue", b"<h1>Right</h1>")):
                root.mkdir()
                (root / "index.html").write_bytes(content)
                (root / "package.json").write_text(json.dumps({"dependencies": {dependency: "1.0"}}), encoding="utf-8")
            parameters = StdioServerParameters(command=sys.executable, args=["-m", "codex_visual_runtime.server"], env=os.environ.copy())
            async with Client(parameters, read_timeout_seconds=20) as client:
                inspections = await asyncio.gather(*(client.call_tool("visual_inspect", {"root": str(root)}) for root in (left, right)))
                self.assertEqual([result.structured_content["frameworks"] for result in inspections], [["react"], ["vue"]])
                jobs = []
                for root, expected in ((left, b"<h1>Left</h1>"), (right, b"<h1>Right</h1>")):
                    result = await client.call_tool("visual_artifacts", {"root": str(root), "paths": ["index.html"]})
                    self.assertEqual(result.structured_content["artifacts"][0]["sha256"], hashlib.sha256(expected).hexdigest())
                    result = await client.call_tool("visual_preview_start", {"root": str(root), "entry": "index.html", "files": ["index.html"]})
                    jobs.append(result.structured_content)
                for job, expected in zip(jobs, (b"<h1>Left</h1>", b"<h1>Right</h1>")):
                    with urllib.request.urlopen(job["url"], timeout=2) as response:
                        self.assertEqual(response.read(), expected)
                result = await client.call_tool("visual_artifacts", {"root": str(left), "paths": ["../右側 project/index.html"]})
                self.assertEqual(result.structured_content["status"], "local_error")
                async with Client(parameters, read_timeout_seconds=20) as other_client:
                    result = await other_client.call_tool("visual_preview_stop", {"job_id": jobs[1]["job_id"]})
                    self.assertEqual(result.structured_content["status"], "unknown_job")
                result = await client.call_tool("visual_preview_stop", {"job_id": jobs[0]["job_id"]})
                self.assertEqual(result.structured_content["status"], "stopped")
                result = await client.call_tool("visual_preview_status", {"job_id": jobs[1]["job_id"]})
                self.assertEqual(result.structured_content["status"], "ready")
            with self.assertRaises(urllib.error.URLError):
                urllib.request.urlopen(jobs[1]["url"], timeout=1)


if __name__ == "__main__":
    unittest.main()
