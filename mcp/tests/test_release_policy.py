"""Focused, offline checks of the actual public Release gates and event wiring."""
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import textwrap
import unittest


ROOT = Path(__file__).resolve().parents[2]
RELEASE_ONLY = "github.event_name == 'release'"
GATE = "Check stable aggregate Release eligibility"
WORKFLOWS = {
    "cli-release.yml": ("tag", {"build": ["eligibility"], "attach": ["build"]}, "attach"),
    "plugin-release.yml": ("revision", {"check": ["eligibility"], "publish": ["check"]}, "publish"),
    "python-tools-release.yml": ("tag", {"source": ["eligibility"], "cli": ["eligibility"], "publish": ["source", "cli"]}, "publish"),
}


def jobs(source):
    # Read only the repository's top-level job blocks; no YAML dependency needed.
    return dict(re.findall(r"^  ([a-z]+):\n(.*?)(?=^  [a-z]+:\n|\Z)", source.split("\njobs:\n", 1)[1], re.M | re.S))


def gate(job):
    blocks = re.findall(r"^      - name: " + GATE + r"\n(.*?)(?=^      - |\Z)", job, re.M | re.S)
    if len(blocks) != 1:
        raise AssertionError("Expected exactly one stable aggregate gate in this job")
    return blocks[0]


def python_block(step):
    return textwrap.dedent(re.search(r"          python - <<'PY'\n(.*?)^          PY$", step, re.M | re.S)[1])


class ReleasePolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = {name: (ROOT / ".github/workflows" / name).read_text(encoding="utf-8") for name in WORKFLOWS}

    def test_every_actual_gate_accepts_only_matching_stable_aggregate_tags(self):
        cases = [
            ("v0.1.0", "0.1.0", "false", False),
            ("v0.99.99", "0.99.99", "false", False),
            ("v1.0.0", "1.0.0", "false", True),
            ("v12.34.56", "12.34.56\n", "false", True),
            ("v1.0.0", "1.0.1", "false", False),
            ("v1.0.0", "0.4.2", "false", False),
            ("v1.0.0", "1.0.0", "true", False),
            ("v1.0.0-rc.1", "1.0.0-rc.1", "false", False),
            ("v1.0.0+build.1", "1.0.0+build.1", "false", False),
            ("1.0.0", "1.0.0", "false", False),
            ("v1", "1", "false", False),
            ("v1.0", "1.0", "false", False),
            ("v01.0.0", "01.0.0", "false", False),
            ("v1.00.0", "1.00.0", "false", False),
            ("v1.0.00", "1.0.00", "false", False),
            ("v1.0.0\n", "1.0.0", "false", False),
        ]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            # A different component VERSION must never satisfy the aggregate gate.
            (root / "python-tools").mkdir()
            (root / "python-tools/VERSION").write_text("1.0.0", encoding="utf-8")
            for name, (_, _, publisher) in WORKFLOWS.items():
                workflow_jobs = jobs(self.sources[name])
                for job_name in ("eligibility", publisher):
                    code = python_block(gate(workflow_jobs[job_name]))
                    for tag, version, prerelease, allowed in cases:
                        with self.subTest(workflow=name, job=job_name, tag=tag, version=version, prerelease=prerelease):
                            (root / "VERSION").write_text(version, encoding="utf-8")
                            result = subprocess.run(
                                [sys.executable, "-B", "-c", code], cwd=root,
                                env={**os.environ, "POLICY_TAG": tag, "POLICY_PRERELEASE": prerelease},
                                capture_output=True, text=True, timeout=10,
                            )
                            self.assertEqual(result.returncode, 0 if allowed else 1, result.stderr)

    def test_release_and_manual_dispatch_wiring(self):
        for name, (input_name, dependencies, publisher) in WORKFLOWS.items():
            with self.subTest(workflow=name):
                source = self.sources[name]
                workflow_jobs = jobs(source)
                self.assertRegex(source, r"(?m)^  release:\n    types: \[published\]$")
                self.assertRegex(source, r"(?m)^  workflow_dispatch:\n    inputs:\n      " + input_name + r":$")
                self.assertRegex(source, r"(?m)^permissions:\n  contents: read$")
                for job_name, required in dependencies.items():
                    expected = required[0] if len(required) == 1 else "[" + ", ".join(required) + "]"
                    self.assertIn("    needs: " + expected + "\n", workflow_jobs[job_name])
                eligibility = workflow_jobs["eligibility"]
                self.assertIn("ref: ${{ github.event.release.tag_name || inputs." + input_name + " || github.sha }}", eligibility)
                self.assertIn("        if: " + RELEASE_ONLY + "\n", gate(eligibility))
                publish = workflow_jobs[publisher]
                self.assertIn("    if: " + RELEASE_ONLY + "\n", publish)
                self.assertIn("      contents: write\n", publish)
                self.assertIn("ref: ${{ github.event.release.tag_name }}", publish)
                self.assertNotIn("        if:", gate(publish))
                for job_name in ("eligibility", publisher):
                    block = workflow_jobs[job_name]
                    step = gate(block)
                    self.assertIn("        working-directory: .\n", step)
                    self.assertIn("POLICY_TAG: ${{ github.event.release.tag_name }}", step)
                    self.assertIn("POLICY_PRERELEASE: ${{ github.event.release.prerelease }}", step)
                    self.assertLess(block.index("uses: actions/checkout@"), block.index(GATE))
                    if job_name == publisher:
                        self.assertLess(block.index(GATE), block.index("gh release upload"))
                for job_name in dependencies:
                    if job_name == publisher:
                        continue
                    block = workflow_jobs[job_name]
                    expected_ref = "${{ env.RELEASE_TAG }}" if name == "python-tools-release.yml" else "${{ github.event.release.tag_name || inputs." + input_name + " }}"
                    self.assertIn("ref: " + expected_ref, block)
                    self.assertNotIn("contents: write", block)
                    self.assertNotIn("gh release upload", block)
                # Manual pre-1.0/revision checks run without Release metadata;
                # eligibility skips its Release-only step, downstream work remains enabled.
                self.assertNotRegex(eligibility, r"(?m)^    if:")
                for job_name in dependencies:
                    if job_name != publisher:
                        self.assertNotRegex(workflow_jobs[job_name], r"(?m)^    if:")

    def test_python_tools_manual_build_uses_component_version_at_aggregate_ref(self):
        source = self.sources["python-tools-release.yml"]
        workflow_jobs = jobs(source)
        self.assertIn("RELEASE_TAG: ${{ inputs.tag || github.event.release.tag_name }}", source)
        component = re.search(r"      - name: Read independent Python tools version\n(.*?)(?=^      - )", workflow_jobs["source"], re.M | re.S)[1]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "VERSION").write_text("1.0.0", encoding="utf-8")
            tools = root / "python-tools"
            tools.mkdir()
            (tools / "VERSION").write_text("0.4.2\n", encoding="utf-8")
            output = root / "output"
            subprocess.run([sys.executable, "-B", "-c", python_block(component)], cwd=tools,
                           env={**os.environ, "GITHUB_OUTPUT": str(output)}, check=True, timeout=10)
            self.assertEqual(output.read_text(encoding="utf-8"), "tag=v0.4.2\n")
        for asset in ("*.zip", "*.whl", "release-manifest.json"):
            self.assertIn("python-tools/dist/${{ steps.component.outputs.tag }}/" + asset, workflow_jobs["source"])
        self.assertIn("$componentTag = 'v' + (Get-Content VERSION -Raw).Trim()", workflow_jobs["cli"])
        self.assertIn('python launch-cli.py scripts.release cli "$componentTag"', workflow_jobs["cli"])
        self.assertIn("CLI_TAG: ${{ github.event.release.tag_name || inputs.version }}", self.sources["cli-release.yml"])


if __name__ == "__main__":
    unittest.main()
