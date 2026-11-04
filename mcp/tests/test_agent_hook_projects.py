import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import project_checks as checks
import install_agent_hooks as installer
import install_project_checks as git_installer


class ProjectChecksTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="project checks '")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / "repo"
        self.root.mkdir()
        self.git("init", "-q")
        self.git("config", "user.name", "Fixture")
        self.git("config", "user.email", "fixture@example.invalid")
        self.git("remote", "add", "origin", "https://github.com/example/project.git")
        (self.root / "data.json").write_text('{}\n')
        self.git("add", "data.json")
        self.git("commit", "-qm", "fixture")
        self.project = {"repository": "https://github.com/example/project.git", "visibility": "public",
                        "deny": ["AGENTS.md", ".agents/*", ".env*", "tests/*"],
                        "allow": [".agents/plugins/marketplace.json", ".env.example"],
                        "checks": [{"id": "json", "kind": "json", "paths": ["*.json"], "exclude": []}],
                        "delivery": ["Review applicable project acceptance"]}
        self.policy = {"project_checks": [{"root": str(self.root), "project": self.project}]}
        self.state = self.base / "state"
        # Installed bundles get the same canonical scanner.
        self.scanner = Path(checks.__file__).with_name("public_content.py")

    def git(self, *args):
        return subprocess.run(["git", *args], cwd=self.root, capture_output=True, check=True)

    def evaluate(self, run=True, session="one"):
        return checks.evaluate(self.root, self.project, self.policy, self.state, "codex", session, run)[0]

    def test_receipt_changes_with_untracked_content_and_session(self):
        f = self.root / "new.json"
        f.write_text('{"ok":1}')
        self.assertEqual("passed", self.evaluate()["checks"][0]["status"])
        f.write_text('{"bad":')
        self.assertEqual("stale", self.evaluate(False)["checks"][0]["status"])
        self.assertEqual("missing", self.evaluate(False, "two")["checks"][0]["status"])
        self.assertEqual("failed", self.evaluate()["checks"][0]["status"])
        self.assertEqual("not_verified", self.evaluate()["project_acceptance"])

    def test_failed_status_is_not_inferred_from_exit_zero_or_old_receipt(self):
        f=self.root/'data.json'; f.write_text('bad')
        self.assertEqual('failed',self.evaluate()['checks'][0]['status'])
        f.write_text('{"new":true}')
        self.assertEqual('stale',self.evaluate(False)['checks'][0]['status'])
        self.assertEqual('passed',self.evaluate()['checks'][0]['status'])

    def test_changed_during_check_cannot_pass(self):
        f=self.root/'data.json';f.write_text('{"start":1}')
        original=checks.perform
        def changed(*args):
            value=original(*args);f.write_text('{"end":2}');return value
        with patch.object(checks,'perform',side_effect=changed):
            self.assertEqual('stale',self.evaluate()['checks'][0]['status'])

    def test_public_path_rules_preserve_marketplace_exception(self):
        self.assertTrue(checks.denied(self.project,'AGENTS.md'))
        self.assertTrue(checks.denied(self.project,'.agents/roles.json'))
        self.assertFalse(checks.denied(self.project,'.agents/plugins/marketplace.json'))

    def test_public_check_reads_index_not_clean_worktree(self):
        f=self.root/'data.json'
        f.write_text('-----BEGIN '+ 'PRIVATE KEY-----\nsynthetic\n')
        self.git('add','data.json'); f.write_text('{}')
        report=checks.public_index(self.root,self.project)
        self.assertEqual('failed',report['status'])
        self.assertNotIn('synthetic',json.dumps(report))

    def test_denied_index_path_is_checked_even_without_content_change(self):
        (self.root/'AGENTS.md').write_text('private guidance')
        self.git('add','AGENTS.md')
        self.assertEqual('failed',checks.public_index(self.root,self.project)['status'])
        self.project['visibility']='private'
        self.assertEqual('not_applicable',checks.public_index(self.root,self.project)['status'])

    def test_unknown_origin_and_checkout_do_not_run(self):
        self.git('remote','set-url','origin','https://github.com/other/project.git')
        self.assertIsNone(checks.selected(self.policy,self.root)[1])

    def test_reentrant_stop_and_duplicate_report_are_quiet(self):
        (self.root/'data.json').write_text('bad')
        payload={'cwd':str(self.root),'session_id':'one','hook_event_name':'Stop'}
        self.assertTrue(checks.lifecycle(payload,self.policy,'codex',self.state))
        self.assertEqual('',checks.lifecycle(payload,self.policy,'codex',self.state))
        self.assertEqual('',checks.lifecycle(dict(payload,stop_hook_active=True),self.policy,'codex',self.state))

    def test_python_check_does_not_execute_or_write_cache(self):
        check={'id':'python','kind':'python','paths':['*.py'],'exclude':[]}
        self.project['checks']=[check]
        (self.root/'danger.py').write_text('raise RuntimeError("must not execute")\n')
        self.assertEqual('passed',self.evaluate()['checks'][0]['status'])
        self.assertFalse((self.root/'__pycache__').exists())

    def test_missing_node_and_budget_do_not_pass(self):
        check={'id':'js','kind':'node','paths':['*.js'],'exclude':[]}
        self.project['checks']=[check]
        (self.root/'x.js').write_text('const x=1;')
        self.assertEqual('unavailable',self.evaluate()['checks'][0]['status'])
        self.assertEqual('deferred',checks.perform(self.root,check,[('x.js',b'x')],{},0)['status'])

    def test_registry_rejects_executable_profile_and_duplicate_identity(self):
        value={'schema_version':1,'projects':[self.project]}
        checks.validate_registry(value)
        with self.assertRaises(ValueError):checks.validate_registry(dict(value,projects=[self.project,self.project]))
        self.project['checks'][0]['command']='echo no'
        with self.assertRaises(ValueError):checks.validate_registry(value)

    def test_compact_registry_preserves_exact_project_exception(self):
        defaults={k:self.project[k] for k in ('deny','allow','checks')}
        row={k:self.project[k] for k in ('repository','visibility','delivery')}
        row['allow_extra']=['AGENTS.md']
        expanded=checks.expand_registry({'schema_version':1,'defaults':defaults,'projects':[row]})
        self.assertFalse(checks.denied(expanded['projects'][0],'AGENTS.md'))
        self.assertTrue(checks.denied(expanded['projects'][0],'.agents/unknown.json'))

    def test_native_git_precommit_preserves_old_hook_and_blocks_private_path(self):
        old=self.root/'.githooks';old.mkdir()
        hook=old/'pre-commit'
        hook.write_text('#!/bin/sh\necho old-hook-ran >&2\n',newline='\n')
        hook.chmod(0o755)
        self.git('config','core.hooksPath','.githooks')
        home=self.base/'home'
        profile={'schema_version':1,'entries':[],'start_note':'Read rules','stop_note':'Report checks'}
        operations=self.base/'operations.md';operations.write_text('operations')
        files,expected=installer.plan('codex',home,profile,operations,Path(sys.executable),Path(shutil.which('git')),sys.platform,self.policy['project_checks'])
        installer.apply_plan(files,expected,home)
        manifest=json.loads((home/'managed-agent-hooks/manifest.json').read_text())
        policy=home/'managed-agent-hooks'/manifest['bundle']/'policy.json'
        updated,_=installer.plan('codex',home,profile,operations,Path(sys.executable),Path(shutil.which('git')),sys.platform)
        persisted=json.loads(next(data for p,data in updated.items() if p.name=='policy.json'))
        self.assertEqual(self.policy['project_checks'],persisted['project_checks'])
        (self.root/'data.json').write_text('bad')
        runner=policy.with_name('agent_hooks.py')
        payload={'cwd':str(self.root),'session_id':'installed','hook_event_name':'PostToolUse'}
        event=subprocess.run([sys.executable,'-I','-B',str(runner),'--client','codex','--policy',str(policy),
                              '--state-dir',str(self.state)],input=json.dumps(payload).encode(),capture_output=True)
        self.assertEqual(0,event.returncode,event.stderr)
        self.assertIn('json:failed',json.loads(event.stdout)['systemMessage'])
        (self.root/'data.json').write_text('{}\n')
        argv=[sys.executable,str(Path(git_installer.__file__)),'--policy',str(policy),'--state-dir',str(self.state),'--checkout',str(self.root)]
        preview=subprocess.run(argv,capture_output=True)
        self.assertEqual(1,preview.returncode,preview.stderr)
        apply=subprocess.run([*argv,'--apply'],capture_output=True)
        self.assertEqual(0,apply.returncode,apply.stderr)
        self.assertEqual(0,subprocess.run(argv,capture_output=True).returncode)
        (self.root/'AGENTS.md').write_text('private')
        self.git('add','AGENTS.md')
        attempt=subprocess.run(['git','commit','-qm','must block'],cwd=self.root,capture_output=True)
        self.assertNotEqual(0,attempt.returncode)
        self.assertIn(b'old-hook-ran',attempt.stderr)
        self.assertEqual('#!/bin/sh\necho old-hook-ran >&2\n',hook.read_text())


if __name__=='__main__':unittest.main()
