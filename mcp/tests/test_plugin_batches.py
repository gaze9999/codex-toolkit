"""Focused source/decision/privacy checks; never stage or build local packages."""
import importlib.util
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
from types import SimpleNamespace
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "mcp/scripts"))
import plugin_catalog
from prepare_plugin_release import prepare


def module(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


activity = module("activity_summary", "skills/local-activity-query/scripts/activity_summary.py")
guide = module("task_guide", "skills/task-guide/scripts/create_task_guide.py")
sys.path.insert(0, str(ROOT / 'mcp/mcp_servers/workspace_inspection'))
from workspace_inspection_mcp import service as workspace_service


class SourceChecks(unittest.TestCase):
    def test_public_batches_are_self_contained(self):
        packages, result = prepare(ROOT)
        self.assertEqual(len(packages), 9)
        self.assertEqual(result["blocked"], [])
        self.assertTrue(all("plugin.json" in files for files, _manifest in packages.values()))
        self.assertIn("resources/proofreading/zh-tw/protected-copy.cjs", packages["multilingual-proofreading"][0])
        documentation, manifest = packages["project-documentation"]
        self.assertIn("skills/readme-maintainer/SKILL.md", documentation)
        self.assertIn("skills/license-maintainer/SKILL.md", documentation)
        self.assertEqual(manifest["runtime_profiles"], [])

    def test_blocked_selection_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Unknown plugin"):
            prepare(ROOT, "workbench-ui")

    def test_escaping_paths_are_rejected(self):
        for path in ("../secret", "/absolute", "C:/private", "folder\\file"):
            with self.subTest(path=path), self.assertRaises(ValueError):
                plugin_catalog.safe_source(ROOT, path)

    def test_config_does_not_claim_loaded_plugins(self):
        rows = plugin_catalog.inventory(ROOT, {"plugins": {"codex-jev-evaluation@example": {"enabled": False}}, "_direct_skills": ["jev-evaluation"]})
        row = next(row for row in rows if row["id"] == "jev-evaluation")
        self.assertFalse(row["enabled"])
        self.assertIsNone(row["loaded"])
        self.assertEqual(row["direct_skills"], ["jev-evaluation"])


class DecisionChecks(unittest.TestCase):
    def record(self, identifier, targets=None):
        return {"id": identifier, "type": "user_decision", "source": "user input", "summary": identifier, "supersedes": targets or []}

    def test_superseded_source_is_retained(self):
        rows = guide.validate_decisions([self.record("A"), self.record("B", ["A"])])
        self.assertEqual([row["status"] for row in rows], ["superseded", "active"])

    def test_bad_relations_are_rejected(self):
        for records in ([self.record("A"), self.record("A")], [self.record("A", ["missing"])], [self.record("A", ["B"]), self.record("B", ["A"])]):
            with self.subTest(records=records), self.assertRaises(ValueError):
                guide.validate_decisions(records)

    def test_legacy_guide_input_still_renders(self):
        content = guide.render(guide.validate({"title": "Example", "scope": ["One feature"], "source_authority": ["Approved source"], "read_by_task": [{"need": "UI", "evidence": "Selected template"}]}))
        self.assertIn("One feature", content)
        self.assertNotIn("## 需求與決策", content)

    def test_long_decision_chain_retains_all_sources(self):
        rows = guide.validate_decisions([self.record(str(index), [str(index-1)] if index else []) for index in range(1400)])
        self.assertEqual(len(rows), 1400)
        self.assertEqual(rows[-1]["status"], "active")


class ActivityChecks(unittest.TestCase):
    def test_projection_preserves_unknown_and_drops_private_details(self):
        snapshot = {"version": 1, "codex": {"health": "partial", "tools": {"exec": 0}, "threads": [{"title": "PRIVATE", "path": "SECRET"}], "error": "PASSWORD"}, "jev": {"summary": {"calls": 0, "input_tokens": None}}, "mcp": {"servers": [{"server": "example", "calls": 2, "payload": "TOKEN"}]}}
        result = activity.project_summary(snapshot, "24h")
        self.assertEqual(result["codex"]["tools"]["exec"], 0)
        self.assertIsNone(result["jev"]["input_tokens"])
        self.assertEqual(result["codex"]["health"], "partial")
        serialized = json.dumps(result)
        for private in ("PRIVATE", "SECRET", "PASSWORD", "TOKEN"):
            self.assertNotIn(private, serialized)

    def test_url_boundary(self):
        self.assertEqual(activity.monitor_port("http://localhost:8891/"), 8891)
        for url in ("https://127.0.0.1:8891", "http://127.0.0.1:0", "http://127.0.0.1:8891/api", "http://user:secret@127.0.0.1:8891", "http://127.0.0.1.evil:8891", "http://127.0.0.1:8891?token=x"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                activity.monitor_port(url)

    def test_redirect_is_not_followed_and_connection_closes(self):
        with patch.object(activity.http.client, "HTTPConnection") as factory:
            client = factory.return_value
            client.getresponse.return_value.status = 302
            with self.assertRaises(ValueError):
                activity.fetch_summary("http://127.0.0.1:8891", "1h")
            client.close.assert_called_once()

    def test_oversize_response_is_rejected(self):
        with patch.object(activity.http.client, "HTTPConnection") as factory:
            response = factory.return_value.getresponse.return_value
            response.status = 200
            response.getheader.return_value = "application/json"
            response.read.return_value = b"x" * (activity.MAX_BYTES + 1)
            with self.assertRaisesRegex(ValueError, "bounded"):
                activity.fetch_summary("http://127.0.0.1:8891", "1h")
            factory.return_value.close.assert_called_once()


class WorkspaceAdapterChecks(unittest.TestCase):
    def service(self, modern=True):
        validation = SimpleNamespace(index_evidence=Mock(return_value={'runs': []}))
        if modern:validation.assess_evidence = lambda *_args: {}
        with patch.object(workspace_service, 'load_core', return_value=SimpleNamespace(validation=validation)):
            return workspace_service.WorkspaceInspectionService([ROOT]), validation

    def test_legacy_request_keeps_two_arguments(self):
        service, core = self.service()
        service.validation_evidence(str(ROOT), 5)
        core.index_evidence.assert_called_once_with(ROOT, 5)

    def test_baseline_request_reuses_the_versioned_core(self):
        service, core = self.service()
        baseline = {'source_revision': 'a' * 40}
        service.validation_evidence(str(ROOT), 5, baseline)
        core.index_evidence.assert_called_once_with(ROOT, 5, baseline)

    def test_old_core_and_unapproved_roots_are_rejected(self):
        service, core = self.service(modern=False)
        with self.assertRaises(RuntimeError):service.validation_evidence(str(ROOT), current={})
        with self.assertRaises(ValueError):service.validation_evidence(str(ROOT.parent))
        core.index_evidence.assert_not_called()


if __name__ == "__main__":
    unittest.main()
