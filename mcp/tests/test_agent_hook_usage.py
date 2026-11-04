import json
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import agent_hooks as hooks
import install_agent_hooks as installer


def counts(inputs, cached, outputs):
    return dict(input_tokens=inputs, cached_input_tokens=cached,
                output_tokens=outputs, total_tokens=inputs + outputs)


def event(kind, **values):
    return {"type": "event_msg", "payload": dict(type=kind, **values)}


def usage(total, last):
    return event("token_count", info={"total_token_usage": total, "last_token_usage": last})


def final(text="done"):
    return {"type": "response_item", "payload": {
        "type": "message", "role": "assistant", "phase": "final_answer",
        "content": [{"type": "output_text", "text": text}]}}


class NativeUsageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="native usage ")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.root = self.base / "sessions"
        self.root.mkdir()
        self.transcript = self.root / "session.jsonl"
        self.state = self.base / "state"
        self.policy = {"codex_token_usage": True, "transcript_root": str(self.root), "git": "git"}
        self.payload = {"hook_event_name": "Stop", "session_id": "session",
                        "turn_id": "current", "transcript_path": str(self.transcript),
                        "last_assistant_message": "done", "cwd": str(self.base)}
        self.header = {"type": "session_meta", "payload": {"id": "session"}}
        self.rows = [self.header, event("task_started", turn_id="previous"),
                     usage(counts(100, 80, 10), counts(100, 80, 10)),
                     event("task_complete", turn_id="previous"),
                     event("task_started", turn_id="current"),
                     usage(counts(150, 120, 15), counts(50, 40, 5)), final(),
                     usage(counts(170, 130, 20), counts(20, 10, 5))]
        self.write()

    def write(self, rows=None):
        self.transcript.write_text("".join(json.dumps(row) + "\n" for row in (rows or self.rows)), encoding="utf-8")

    def message(self, client="codex"):
        return hooks.usage_message(self.payload, self.policy, client, self.state)

    def test_multiple_requests_use_turn_delta_and_deduplicate(self):
        self.rows.append(self.rows[-1])
        self.write()
        self.assertEqual(counts(70, 50, 10), hooks.transcript_usage(self.payload, self.root))
        self.assertEqual("Codex 本輪用量: 總計 80 tokens (輸入 70, 輸出 10, 快取輸入 50)", self.message())
        self.assertIsNone(self.message())
        receipt = json.loads(next(self.state.glob("usage-*.json")).read_text())
        self.assertEqual(counts(70, 50, 10), receipt["usage"])
        self.assertNotIn("done", json.dumps(receipt))

    def test_first_turn_requires_zero_origin(self):
        self.write([self.header, event("task_started", turn_id="current"),
                    final(), usage(counts(30, 10, 4), counts(30, 10, 4))])
        self.assertEqual(counts(30, 10, 4), hooks.transcript_usage(self.payload, self.root))
        self.write([self.header, event("task_started", turn_id="current"),
                    final(), usage(counts(130, 90, 14), counts(30, 10, 4))])
        self.assertIsNone(self.message())

    def test_missing_intermediate_receipt_never_reports_partial_total(self):
        del self.rows[5]
        self.write()
        self.assertIsNone(self.message())

    def test_final_usage_must_follow_matching_final_message(self):
        for rows in (self.rows[:-1], self.rows[:6] + [self.rows[-1], final()],
                     self.rows[:6] + [final("different"), self.rows[-1]]):
            self.write(rows)
            self.assertIsNone(self.message())

    def test_stale_turn_and_other_session_stay_silent(self):
        self.rows.append(event("task_started", turn_id="newer"))
        self.write()
        self.assertIsNone(self.message())
        self.write(self.rows[:-1])
        self.payload["session_id"] = "other-session"
        self.assertIsNone(self.message())

    def test_partial_line_or_invalid_json_stays_silent(self):
        data = self.transcript.read_bytes()
        for suffix in (b'{"type":', b'invalid-json\n'):
            self.transcript.write_bytes(data + suffix)
            if suffix.endswith(b"\n"):
                # Native-looking malformed records cannot become a valid receipt.
                self.transcript.write_bytes(data + b'{"type":"event_msg","payload":{"type":"token_count","info":invalid}}\n')
            self.assertIsNone(self.message())

    def test_counter_reset_and_invalid_types_stay_silent(self):
        for total in (counts(20, 10, 5), dict(counts(170, 130, 20), total_tokens=True),
                      dict(counts(170, 130, 20), total_tokens=999), counts(170, 200, 20)):
            self.write(self.rows[:-1] + [usage(total, counts(20, 10, 5))])
            self.assertIsNone(self.message())

    def test_missing_fields_and_unsupported_format_stay_silent(self):
        for key in ("turn_id", "transcript_path", "last_assistant_message"):
            with self.subTest(key=key):
                value = self.payload.pop(key)
                self.assertIsNone(self.message())
                self.payload[key] = value
        self.write([self.header, event("turn_started", turn_id="current"), final(), self.rows[-1]])
        self.assertIsNone(self.message())

    def test_transcript_outside_root_is_not_opened(self):
        outside = self.base / "outside.jsonl"
        outside.write_bytes(self.transcript.read_bytes())
        self.payload["transcript_path"] = str(outside)
        self.assertIsNone(self.message())

    def test_tail_limit_without_turn_baseline_stays_silent(self):
        with patch.object(hooks, "MAX_TRANSCRIPT", 400):
            self.assertIsNone(self.message())

    def test_prompt_records_are_not_parsed(self):
        data = self.transcript.read_bytes()
        prompt = b'{"type":"event_msg","payload":{"type":"user_message","message":"' + b'x' * 4096 + b'"}}\n'
        header, remaining = data.split(b"\n", 1)
        self.transcript.write_bytes(header + b"\n" + prompt + remaining)
        with patch.object(hooks, "MAX_INPUT", 2048):
            self.assertIn("總計 80 tokens", self.message())

    def test_disabled_claude_and_continuation_do_not_read_transcript(self):
        with patch.object(hooks, "transcript_usage", side_effect=AssertionError("unexpected read")):
            self.assertIsNone(self.message("claude"))
            self.policy["codex_token_usage"] = False
            self.assertIsNone(self.message())
            self.policy["codex_token_usage"] = True
            self.payload["stop_hook_active"] = True
            self.assertIsNone(self.message())

    def test_usage_works_outside_git_and_preserves_workspace_warning(self):
        with patch.object(hooks, "git_run", return_value=(128, b"")):
            self.assertIn("總計 80 tokens", hooks.handle(self.payload, self.policy, "codex", self.state)["systemMessage"])
        self.payload["turn_id"] = "current"
        other_state = self.base / "other-state"
        with patch.object(hooks, "workspace_event", return_value={"systemMessage": "existing warning"}):
            output = hooks.handle(self.payload, self.policy, "codex", other_state)
            self.assertTrue(output["systemMessage"].startswith("existing warning\nCodex 本輪用量:"))

    def test_profile_option_is_explicit_and_codex_only(self):
        profile = {"schema_version": 1, "entries": [], "start_note": "", "stop_note": ""}
        installer.validate_profile(profile)
        profile["codex_token_usage"] = True
        installer.validate_profile(profile)
        operations = self.base / "operations.md"
        operations.write_text("# Operations\n")
        for client in ("codex", "claude"):
            home = self.base / client
            files, _ = installer.plan(client, home, profile, operations, Path(sys.executable), Path("git"), sys.platform)
            policy = next(json.loads(data) for path, data in files.items() if path.name == "policy.json")
            self.assertEqual(client == "codex", "transcript_root" in policy)
        for value in (1, "true", None):
            profile["codex_token_usage"] = value
            with self.assertRaises(ValueError):
                installer.validate_profile(profile)

    def test_installed_stop_command_reports_native_fixture_and_skips_missing_data(self):
        home = self.base / "installed-codex"
        sessions = home / "sessions"
        sessions.mkdir(parents=True)
        transcript = sessions / "native.jsonl"
        transcript.write_bytes(self.transcript.read_bytes())
        profile = {"schema_version": 1, "entries": [], "start_note": "", "stop_note": "",
                   "codex_token_usage": True}
        operations = self.base / "operations.md"
        operations.write_text("# Operations\n")
        files, expected = installer.plan("codex", home, profile, operations,
                                         Path(sys.executable), Path(shutil.which("git")), sys.platform)
        installer.apply_plan(files, expected, home)
        config = json.loads((home / "hooks.json").read_text())
        command = shlex.split(config["hooks"]["Stop"][0]["hooks"][0]["command"])
        payload = dict(self.payload, transcript_path=str(transcript))
        result = subprocess.run(command, input=json.dumps(payload).encode(), capture_output=True, timeout=20)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("總計 80 tokens", json.loads(result.stdout)["systemMessage"])
        payload["transcript_path"] = None
        result = subprocess.run(command, input=json.dumps(payload).encode(), capture_output=True, timeout=20)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual({}, json.loads(result.stdout))


if __name__ == "__main__":
    unittest.main()
