"""Offline acceptance for source assembly, component mappings and measured evaluation."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "mcp/scripts"))
import plugin_catalog
import prepare_plugin_release as plugins
import prepare_mcp_release as mcp_packages
from prepare_release import read_skill, snapshot


def module(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


packaging = module("setup_packaging", "tooling/package.py")
evaluation = module("setup_evaluation", "tooling/evaluate.py")


class PackagingChecks(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve() / "source"
        self.root.mkdir()
        self.write("skills/example/SKILL.md", "---\nname: example\ndescription: Example workflow\n---\nRun example\n")
        self.write("mcp/tools/development-tools.requirements.json", '{"tools":{}}')
        self.write("mcp/mcp_servers/presets/baseline.json", '{"servers":[]}')
        self.bundle = {"id":"example", "batch":"test", "status":"ready", "skills":["example"], "runtime_profiles":[], "resources":[]}
        self.write("plugins/catalog.json", json.dumps({"schema_version":1, "bundles":[self.bundle]}))
        self.write("plugins/example/plugin.json", json.dumps({"$schema":plugin_catalog.SCHEMA, "name":"codex-example", "version":"1.0.0", "description":"Example"}))
        self.write("tooling/products.json", json.dumps({"schema_version":1, "products":[{"id":"skills", "kind":"source", "default":True, "sources":["skills"], "strip_prefix":"skills/", "description":"Skills", "requires":[]}]}))

    def write(self, name, text):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def packages(self):
        return plugins.prepare(self.root)[0]

    def test_source_root_alias_preserves_relative_provenance(self):
        (self.root / "child").mkdir()
        alias = self.root / "child" / ".."
        files, manifest = plugins.prepare(alias)[0]["example"]
        self.assertEqual(manifest["files"]["plugin.json"]["source"], "plugins/example/plugin.json")
        self.assertIn("skills/example/SKILL.md", files)
        product = packaging.products(alias, ["skills"])[0]
        files, provenance = packaging.source_payload(alias, product)
        self.assertEqual(provenance["example/SKILL.md"]["source"], "skills/example/SKILL.md")

    def test_selected_roots_exclude_local_tests_and_caches(self):
        self.write("skills/example/tests/test_private.py", "private fixture")
        self.write("skills/example/.git/config", "local repo")
        self.write("skills/example/.venv/private.txt", "local environment")
        files = self.packages()["example"][0]
        self.assertEqual(set(files), {"plugin.json", "skills/example/SKILL.md"})

    def test_explicit_component_cannot_include_vcs_or_cache_material(self):
        for source in (".git/config", "node_modules/private.json", "dist/generated.json"):
            self.write(source, "private")
            self.bundle["components"] = [{"source":source, "target":"resources/private.json"}]
            self.write("plugins/catalog.json", json.dumps({"schema_version":1, "bundles":[self.bundle]}))
            with self.subTest(source=source), self.assertRaisesRegex(ValueError, "excluded"):
                self.packages()

    def test_link_rejection_even_when_native_creation_is_unavailable(self):
        path = self.root / "skills/example/SKILL.md"
        native_check = Path.is_symlink
        with patch.object(Path, "is_symlink", lambda candidate: candidate == path or native_check(candidate)):
            with self.assertRaises(ValueError):
                plugin_catalog.safe_source(self.root, "skills/example/SKILL.md")

    def test_source_drift_is_rejected_before_promoting_plugin_output(self):
        output = Path(self.temporary.name).resolve() / "drifted"
        packages = self.packages()
        self.write("skills/example/SKILL.md", "changed since preparation")
        with patch.object(plugins, "snapshot_identity", return_value={"source_revision":"a"*40, "source_state":"working-tree"}):
            with self.assertRaisesRegex(ValueError, "Source changed"):
                plugins.write_release(self.root, output, packages, development=True)
        self.assertFalse(output.exists())

    def test_selected_credentials_are_rejected(self):
        for name in (".ENV", "auth.json", "credentials.json", "id_rsa", "private.PFX"):
            path = self.write("skills/example/" + name, "sensitive")
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, "Private material"):
                self.packages()
            path.unlink()

    def test_path_traversal_and_noncanonical_paths_are_rejected(self):
        for name in ("../secret", "a/../../secret", "a//b", "./a", "/secret", "C:/secret", "a\\b"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                plugin_catalog.safe_source(self.root, name)

    def test_internal_link_is_rejected(self):
        link = self.root / "skills/example/link.txt"
        try:
            link.symlink_to(self.root / "skills/example/SKILL.md")
        except OSError:
            self.skipTest("OS does not grant symlink creation")
        with self.assertRaises(ValueError):
            self.packages()

    def test_standalone_skill_does_not_require_plugin_owner(self):
        self.write("skills/unowned/SKILL.md", "unowned")
        self.assertEqual(set(self.packages()), {"example"})

    def test_source_products_include_license_without_prefixing_skill_paths(self):
        license_path = self.write("LICENSE", "MIT fixture")
        product = packaging.products(self.root, ["skills"])[0]
        files, provenance = packaging.source_payload(self.root, product)
        self.assertEqual(files["LICENSE"], license_path.read_bytes())
        self.assertEqual(provenance["LICENSE"]["source"], "LICENSE")
        self.assertIn("example/SKILL.md", files)

    def test_application_source_contains_independent_tools_and_no_private_ui(self):
        product = packaging.products(ROOT, ["application-source"])[0]
        files, _provenance = packaging.source_payload(ROOT, product)
        self.assertIn("python-tools/pyproject.toml", files)
        self.assertIn("mcp/scripts/prepare_cli_release.py", files)
        self.assertIn("LICENSE", files)
        self.assertFalse(any(name.startswith(("launch-gui", "launch-web", "mcp/scripts/_workbench/", "profiles/")) for name in files))

    def test_component_mapping_bundles_mcp_configuration(self):
        self.write("components/mcp.json", json.dumps({"$schema":"https://agent-plugins.org/schemas/1.0.0/mcp.schema.json", "mcpServers":{"example":{"type":"stdio", "command":"example-runtime"}}}))
        self.bundle["components"] = [{"source":"components/mcp.json", "target":"mcp.json"}]
        self.write("plugins/catalog.json", json.dumps({"schema_version":1, "bundles":[self.bundle]}))
        self.assertIn("mcp.json", self.packages()["example"][0])

    def test_mcp_only_plugin_can_be_packaged(self):
        self.test_component_mapping_bundles_mcp_configuration()
        self.bundle["skills"] = []
        (self.root / "skills/example/SKILL.md").unlink()
        self.write("plugins/catalog.json", json.dumps({"schema_version":1, "bundles":[self.bundle]}))
        self.assertEqual(set(self.packages()["example"][0]), {"plugin.json", "mcp.json"})

    def test_external_example_keeps_its_source_and_internal_references(self):
        name = "agents/references/angular-style.md"
        source = self.write(name, "[Member rules](../../skills/example/SKILL.md)\n")
        self.bundle["components"] = [{"source": name, "target": name}]
        self.write("plugins/catalog.json", json.dumps({"schema_version":1, "bundles":[self.bundle]}))
        files, manifest = self.packages()["example"]
        self.assertEqual(files[name], source.read_bytes())
        self.assertEqual(manifest["files"][name]["source"], name)
        source.write_text("[Missing](../../skills/unbundled/SKILL.md)\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Unbundled reference"):
            self.packages()

    def test_angular_references_work_in_standalone_and_plugin_packages(self):
        bundle = next(row for row in plugin_catalog.load_catalog(ROOT) if row["id"] == "frontend-engineering")
        plugin_files, _manifest = plugin_catalog.payload(ROOT, bundle)
        # This also validates all links without a sibling Skill or agents tree.
        standalone_files, _manifest = plugin_catalog.payload(ROOT, {**bundle, "skills": ["angular-development"], "components": []})
        product = packaging.products(ROOT, ["skills"])[0]
        source_files, _provenance = packaging.source_payload(ROOT, product)
        legacy_files = snapshot(ROOT, [read_skill(ROOT / "skills/angular-development/SKILL.md")])
        for resource in ("angular-style.md", "code-maintainability.md"):
            target = "angular-development/references/" + resource
            raw = (ROOT / "skills" / target).read_bytes()
            self.assertEqual(plugin_files["skills/" + target], raw)
            self.assertEqual(standalone_files["skills/" + target], raw)
            self.assertEqual(source_files[target], raw)
            self.assertEqual(legacy_files[target][1], raw)
        self.assertIn("agents/references/angular-style.md", plugin_files)

    def test_mcp_requires_transport_and_empty_plugins_fail(self):
        with self.assertRaises(ValueError):
            plugin_catalog.validate_components({}, {})
        with self.assertRaises(ValueError):
            plugin_catalog.validate_components({"mcp.json":b'{"mcpServers":{"x":{"command":"run"}}}'}, {})

    def test_ui_review_is_self_contained_in_all_skill_packages(self):
        bundle = next(row for row in plugin_catalog.load_catalog(ROOT) if row["id"] == "frontend-engineering")
        plugin_files, _manifest = plugin_catalog.payload(ROOT, bundle)
        standalone_files, _manifest = plugin_catalog.payload(ROOT, {**bundle, "skills": ["ui-ux-design"], "components": []})
        source_files, _provenance = packaging.source_payload(ROOT, packaging.products(ROOT, ["skills"])[0])
        legacy_files = snapshot(ROOT, [read_skill(ROOT / "skills/ui-ux-design/SKILL.md")])
        target = "ui-ux-design/references/detail-review.md"
        raw = (ROOT / "skills" / target).read_bytes()
        self.assertEqual(plugin_files["skills/" + target], raw)
        self.assertEqual(standalone_files["skills/" + target], raw)
        self.assertEqual(source_files[target], raw)
        self.assertEqual(legacy_files[target][1], raw)

    def test_app_mapping_must_be_bundled_and_nonempty(self):
        manifest = {"extensions":{"com.openai":{"apps":"./.app.json"}}}
        for files in ({}, {".app.json":b'{"apps":{}}'}):
            with self.assertRaises(ValueError):
                plugin_catalog.validate_components(files, manifest)
        plugin_catalog.validate_components({".app.json":b'{"apps":{"test_fixture_registered_id":{}}}'}, manifest)

    def test_component_cannot_overwrite_manifest_or_collide_by_case(self):
        self.write("components/data.json", "{}")
        for target in ("PLUGIN.JSON", "source-manifest.json", "skills/example/skill.md", "skills/example"):
            self.bundle["components"] = [{"source":"components/data.json", "target":target}]
            self.write("plugins/catalog.json", json.dumps({"schema_version":1, "bundles":[self.bundle]}))
            with self.subTest(target=target), self.assertRaises(ValueError):
                self.packages()

    def test_source_manifest_target_is_reserved_case_insensitively(self):
        self.write("skills/Source-Manifest.json", "{}")
        with self.assertRaises(ValueError):
            packaging.plan(self.root)

    def test_plugin_archives_are_reproducible_and_verified(self):
        first, second = Path(self.temporary.name).resolve() / "one", Path(self.temporary.name).resolve() / "two"
        with patch.object(plugins, "snapshot_identity", return_value={"source_revision":"a"*40, "source_state":"working-tree"}):
            packages = self.packages()
            plugins.write_release(self.root, first, packages, development=True)
            plugins.write_release(self.root, second, packages, development=True)
            self.assertEqual({path.name:path.read_bytes() for path in first.iterdir()}, {path.name:path.read_bytes() for path in second.iterdir()})
            archive = first / "codex-example-1.0.0.zip"
            archive.write_bytes(archive.read_bytes() + b"tampered")
            with self.assertRaises(ValueError):
                plugins.verify_release(self.root, first, packages, development=True)

    def test_failed_verification_does_not_promote_partial_output(self):
        output = Path(self.temporary.name).resolve() / "failed"
        with patch.object(plugins, "snapshot_identity", return_value={"source_revision":"a"*40, "source_state":"working-tree"}), patch.object(plugins, "verify_release", side_effect=ValueError("readback failed")):
            with self.assertRaises(ValueError):
                plugins.write_release(self.root, output, self.packages(), development=True)
        self.assertFalse(output.exists())
        self.assertEqual({path.name for path in output.parent.iterdir()}, {"source"})

    def test_source_build_preserves_inputs_and_output_ownership(self):
        output = Path(self.temporary.name).resolve() / "built"
        before = (self.root / "skills/example/SKILL.md").read_bytes()
        with patch.object(packaging, "source_identity", return_value={"base_revision":"a"*40, "source_state":"working-tree"}):
            packaging.build(self.root, None, "1.2.3", output)
        self.assertEqual(before, (self.root / "skills/example/SKILL.md").read_bytes())
        self.assertEqual(packaging.verify_output(output)["status"], "verified")
        with zipfile.ZipFile(output / "skills/codex-toolkit-skills-v1.2.3.zip") as stream:
            self.assertIn("example/SKILL.md", stream.namelist())
            self.assertEqual(json.loads(stream.read("source-manifest.json"))["source_state"], "working-tree")
        with self.assertRaises(ValueError):
            packaging.build(self.root, None, "1.2.3", output)
        (output / "extra.txt").write_text("unexpected")
        with self.assertRaises(ValueError):
            packaging.verify_output(output)

    def test_plan_does_not_call_builders_or_create_output(self):
        before = set(self.root.rglob("*"))
        with patch.object(packaging, "build", side_effect=AssertionError("not read-only")):
            self.assertEqual(packaging.plan(self.root)["status"], "planned")
        self.assertEqual(before, set(self.root.rglob("*")))

    def test_release_requires_clean_committed_inputs(self):
        with patch.object(packaging.subprocess, "check_output", side_effect=[str(self.root), "a"*40, " M changed.py"]):
            with self.assertRaisesRegex(ValueError, "clean source tree"):
                packaging.source_identity(self.root, True)

    def test_installer_resources_include_new_toolkit_and_protected_boundaries(self):
        destination = Path(self.temporary.name).resolve() / "installer"
        mcp_packages.copy_installer_resources(ROOT, destination)
        for source in ("tooling/package.py", "tooling/evaluate.py", "tooling/products.json", "evals/routing.json", "evals/benchmark.json", "docs/operating-model.md", "mcp/scripts/prepare_release.py"):
            self.assertEqual((destination / source).read_bytes(), (ROOT / source).read_bytes())
        for name in ("tests", ".codex", ".git", ".env"):
            self.assertFalse((destination / name).exists())


class EvaluationChecks(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.path = Path(self.temporary.name).resolve() / "runs.jsonl"

    def records(self, rows):
        self.path.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")
        return self.path

    def test_fixtures_do_not_claim_behavioral_pass(self):
        result = evaluation.routing(ROOT)
        self.assertEqual(result["status"], "fixtures_validated")
        self.assertIn("unverified", result["behavior"])

    def test_missing_observations_remain_incomplete(self):
        self.path.write_text('[{"case_id":"prompt-direct-fix","selected":[]}]')
        result = evaluation.routing(ROOT, self.path)
        self.assertEqual(result["status"], "incomplete_or_failed")
        self.assertTrue(result["unobserved"])

    def test_pairing_keeps_unknown_usage_null(self):
        rows = [{"case_id":"simple-fix", "trial":1, "variant":variant, "accepted":True, "duration_seconds":seconds, "input_tokens":None, "validation":"passed"} for variant, seconds in (("before", 9), ("after", 6))]
        rows.append({"case_id":"docs", "trial":1, "variant":"after", "duration_seconds":900})
        result = evaluation.compare(ROOT, self.records(rows))
        self.assertEqual(result["paired_runs"], 1)
        self.assertEqual(result["unpaired_runs"], 1)
        self.assertIsNone(result["metrics"]["input_tokens"]["after"])
        self.assertEqual(result["metrics"]["duration_seconds"]["after"], 6)

    def test_source_content_and_unsafe_metric_values_are_rejected(self):
        base = {"case_id":"simple-fix", "trial":1, "variant":"before"}
        for extra in ({"prompt":"private"}, {"path":"private"}, {"tool_calls":True}, {"retries":-1}, {"duration_seconds":float("nan")}, {"model":"secret with spaces"}):
            with self.subTest(extra=extra), self.assertRaises(ValueError):
                evaluation.run_records(self.records([{**base, **extra}]), {"simple-fix"})

    def test_duplicate_trials_are_rejected(self):
        row = {"case_id":"simple-fix", "trial":1, "variant":"before"}
        with self.assertRaises(ValueError):
            evaluation.run_records(self.records([row, row]), {"simple-fix"})


if __name__ == "__main__":
    unittest.main()
