import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import urllib.error
import urllib.request
from codex_visual_runtime.core import Workspace, Previews, Problem


class VisualTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "index.html").write_text("<h1>Preview</h1>", encoding="utf-8")
        (self.root / ".env").write_text("secret", encoding="utf-8")
        self.workspace = Workspace(self.root)
        self.previews = Previews(self.workspace)

    def tearDown(self):
        self.previews.close()
        self.temp.cleanup()

    def test_project_inspection_is_declarative(self):
        (self.root / "package.json").write_text(json.dumps({"dependencies": {"@angular/core": "^20", "three": "^0.180"}, "scripts": {"dev": "never-run"}}), encoding="utf-8")
        result = self.workspace.inspect()
        self.assertEqual(result["frameworks"], ["angular", "three"])
        self.assertEqual(result["scripts"], ["dev"])

    def test_hash_matches_original(self):
        result = self.workspace.artifacts(["index.html"])
        self.assertEqual(result["artifacts"][0]["bytes"], 16)

    def test_empty_root_rejected(self):
        for root in ("", "   "):
            with self.subTest(root=root), self.assertRaises(Problem):
                Workspace(root)

    def test_unbound_preview_requires_call_workspace(self):
        previews = Previews()
        try:
            with self.assertRaisesRegex(Problem, "invalid_root"):
                previews.start("index.html", ["index.html"])
        finally:
            previews.close()

    def test_per_call_previews_are_isolated(self):
        other = self.root / "other project"
        other.mkdir()
        (other / "index.html").write_text("<h1>Other</h1>", encoding="utf-8")
        previews = Previews()
        try:
            first = previews.start("index.html", ["index.html"], workspace=self.workspace)
            second = previews.start("index.html", ["index.html"], workspace=Workspace(other))
            for job, expected in ((first, b"<h1>Preview</h1>"), (second, b"<h1>Other</h1>")):
                with urllib.request.urlopen(job["url"], timeout=2) as response:
                    self.assertEqual(response.read(), expected)
            previews.stop(first["job_id"])
            self.assertEqual(previews.status(second["job_id"])["status"], "ready")
        finally:
            previews.close()

    def test_process_job_limit_across_roots(self):
        other = self.root / "other"
        other.mkdir()
        (other / "index.html").write_text("<h1>Other</h1>", encoding="utf-8")
        workspaces = (self.workspace, Workspace(other))
        previews = Previews()
        try:
            for index in range(8):
                previews.start("index.html", ["index.html"], workspace=workspaces[index % 2])
            with self.assertRaisesRegex(Problem, "job_limit"):
                previews.start("index.html", ["index.html"], workspace=workspaces[1])
        finally:
            previews.close()

    def test_cli_keeps_explicit_root(self):
        result = subprocess.run([sys.executable, "-B", "-m", "codex_visual_runtime", "--root", str(self.root), "inspect"], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["root"], str(self.root.resolve()))

    def test_preview_start_does_not_resolve_hostnames(self):
        with patch("socket.getfqdn", side_effect=AssertionError("Unexpected DNS lookup")):
            job = self.previews.start("index.html", ["index.html"])
        self.assertEqual(job["status"], "ready")
        with urllib.request.urlopen(job["url"], timeout=2) as response:
            self.assertEqual(response.read(), b"<h1>Preview</h1>")

    def test_unicode_space_root_and_relative_assets(self):
        root = self.root / "專案 with spaces"
        root.mkdir()
        (root / "index.html").write_text("<h1>UTF-8</h1>", encoding="utf-8")
        with self.subTest(root=str(root)):
            previews = Previews(Workspace(root))
            try:
                job = previews.start("index.html", ["index.html"])
                with urllib.request.urlopen(job["url"]) as response:
                    self.assertEqual(response.read(), b"<h1>UTF-8</h1>")
            finally:
                previews.close()

    def test_linked_asset_rejected(self):
        link = self.root / "linked.html"
        try:
            link.symlink_to(self.root / "index.html")
        except OSError as error:
            if getattr(error, "winerror", None) == 1314:
                self.skipTest("Windows host lacks symlink creation privilege")
            raise
        with self.assertRaisesRegex(Problem, "linked_path"):
            self.previews.start("linked.html", ["linked.html"])

    def test_escape_and_secret_manifest_rejected(self):
        for name in ("../outside.html", "C:/secret.html", ".env"):
            with self.subTest(name=name), self.assertRaises((Problem, OSError)):
                self.previews.start(name, [name])

    def test_preview_snapshot_stop_and_unknown_owner(self):
        job = self.previews.start("index.html", ["index.html"])
        self.assertEqual(job["status"], "ready")
        with urllib.request.urlopen(job["url"]) as result:
            self.assertEqual(result.read(), b"<h1>Preview</h1>")
        (self.root / "index.html").write_text("changed", encoding="utf-8")
        with urllib.request.urlopen(job["url"]) as result:
            self.assertEqual(result.read(), b"<h1>Preview</h1>")
        self.assertEqual(self.previews.stop("someone-else")["status"], "unknown_job")
        self.assertEqual(self.previews.stop(job["job_id"])["status"], "stopped")
        with self.assertRaises(urllib.error.URLError):
            urllib.request.urlopen(job["url"], timeout=1)

    def test_no_directory_listing_traversal_or_host_rebinding(self):
        job = self.previews.start("index.html", ["index.html"])
        for path in ("", ".env", "../.env", "%2e%2e/.env"):
            with self.assertRaises(urllib.error.HTTPError):
                urllib.request.urlopen(job["url"].removesuffix("index.html") + path)
        req = urllib.request.Request(job["url"], headers={"Host": "untrusted.invalid"})
        with self.assertRaises(urllib.error.HTTPError) as caught:
            urllib.request.urlopen(req)
        self.assertEqual(caught.exception.code, 403)

    def test_manifest_bounds_and_owned_cleanup(self):
        with self.assertRaises(Problem):
            self.previews.start("index.html", ["index.html", "index.html"])
        first = self.previews.start("index.html", ["index.html"])
        second = self.previews.start("index.html", ["index.html"])
        self.previews.stop(first["job_id"])
        self.assertEqual(self.previews.status(second["job_id"])["status"], "ready")


if __name__ == "__main__":
    unittest.main()
