import os
import sys
import unittest
from mcp import Client
from mcp.client.stdio import StdioServerParameters


class ProtocolTests(unittest.IsolatedAsyncioTestCase):
    async def test_offline_tools_and_credential_gate(self):
        env = {**os.environ, "OPENAI_API_KEY": ""}
        parameters = StdioServerParameters(command=sys.executable, args=["-m", "codex_decisions.server"], env=env)
        async with Client(parameters, read_timeout_seconds=20) as client:
            names = sorted(tool.name for tool in (await client.list_tools()).tools)
            self.assertEqual(names, ["decisions_evaluate", "decisions_status", "decisions_validate"])
            request = {"input": "public synthetic evidence", "questions": [{"type": "predicate", "name": "check", "instructions": "Is evidence present?"}]}
            result = await client.call_tool("decisions_validate", {"request": request})
            self.assertFalse(result.is_error)
            self.assertEqual(result.structured_content["status"], "validated")
            result = await client.call_tool("decisions_evaluate", {"request": request})
            self.assertEqual(result.structured_content["status"], "approval_required")
            result = await client.call_tool("decisions_evaluate", {"request": request, "approved": True})
            self.assertEqual(result.structured_content["status"], "needs_credentials")
            result = await client.call_tool("decisions_status", {})
            self.assertEqual(result.structured_content["status"], "needs_credentials")


if __name__ == "__main__":
    unittest.main()
