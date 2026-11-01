import os
import sys
import tempfile
from pathlib import Path
import unittest
import urllib.request
from mcp import Client
from mcp.client.stdio import StdioServerParameters


class ProtocolTests(unittest.IsolatedAsyncioTestCase):
    async def test_owned_preview_through_stdio(self):
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / "index.html").write_text("<h1>Protocol fixture</h1>", encoding="utf-8")
            parameters = StdioServerParameters(command=sys.executable, args=["-m", "codex_visual_runtime.server", "--root", directory], env=os.environ.copy())
            async with Client(parameters, read_timeout_seconds=20) as client:
                names = sorted(tool.name for tool in (await client.list_tools()).tools)
                self.assertEqual(names, ["visual_artifacts", "visual_inspect", "visual_preview_start", "visual_preview_status", "visual_preview_stop"])
                result = await client.call_tool("visual_inspect", {})
                self.assertEqual(result.structured_content["status"], "ok")
                result = await client.call_tool("visual_artifacts", {"paths": ["index.html"]})
                self.assertEqual(result.structured_content["artifacts"][0]["bytes"], 25)
                result = await client.call_tool("visual_preview_start", {"entry": "index.html", "files": ["index.html"]})
                job = result.structured_content
                self.assertEqual(job["status"], "ready")
                with urllib.request.urlopen(job["url"]) as response:
                    self.assertIn(b"Protocol fixture", response.read())
                result = await client.call_tool("visual_preview_status", {"job_id": job["job_id"]})
                self.assertEqual(result.structured_content["status"], "ready")
                result = await client.call_tool("visual_preview_stop", {"job_id": job["job_id"]})
                self.assertEqual(result.structured_content["status"], "stopped")


if __name__ == "__main__":
    unittest.main()
