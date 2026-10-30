"""Synthetic fixtures only; never import application code or install dependencies."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / 'skills/angular-development/scripts/check_maintainability.py'
if not SCRIPT.exists():
    SCRIPT = Path(__file__).with_name('check_maintainability.py')
spec = importlib.util.spec_from_file_location('maintenance', SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class SelectionTests(unittest.TestCase):
    def test_boundaries(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            with self.assertRaises(ValueError):
                module.bounded(root, '../outside.ts')
            self.assertEqual(module.bounded(root, 'inside.ts'), root / 'inside.ts')


@unittest.skipUnless(os.environ.get('TYPESCRIPT_PATH'), 'Set TYPESCRIPT_PATH to an approved installed dependency')
class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.root = self.home / 'input'
        self.root.mkdir()
        self.report = self.home / 'report.json'

    def write(self, name, text):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding='utf-8')
        return path

    def run_review(self, files, extra=(), profile=None):
        args = [sys.executable, '-B', str(SCRIPT), '--root', str(self.root), '--scope', '.', '--mode', 'files',
                '--typescript', os.environ['TYPESCRIPT_PATH'], '--report', str(self.report)]
        for name in files:
            args += ['--file', name]
        if profile:
            config = self.home / 'profile.json'
            config.write_text(json.dumps({'id': 'synthetic', 'version': '1', **profile}))
            args += ['--profile', str(config)]
        before = {p: p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        result = subprocess.run(args + list(extra), capture_output=True, text=True, timeout=90)
        for path, data in before.items():
            self.assertEqual(path.read_bytes(), data)
        self.assertTrue(self.report.exists(), result.stderr)
        report = json.loads(self.report.read_text(encoding='utf-8'))
        self.assertEqual(result.returncode, report['exitCode'])
        return report

    def test_static_candidates_do_not_copy_literals_or_infer_orphans(self):
        self.write('a.ts', 'import {A} from "./dep"; import type {B} from "./dep"; class Item { ngOnInit() {} run(x: any) { return this.other(x); } other(x: unknown) { return x; } } const secret = "PRIVATE_SENTINEL";')
        report = self.run_review(['a.ts'])
        ids = {r['ruleId'] for r in report['results']}
        self.assertTrue({'IMPORT.DUPLICATE', 'TYPE.EXPLICIT_ANY', 'CHAIN.FORWARD'} <= ids)
        self.assertNotIn('PRIVATE_SENTINEL', self.report.read_text())
        self.assertFalse(report['complete'])
        self.assertEqual(next(r for r in report['results'] if r['ruleId'] == 'ORPHAN.CONSUMERS')['status'], 'MANUAL')
        self.assertNotIn('MEMBER.VISIBILITY', ids)

    def test_parse_failure_keeps_independent_files(self):
        self.write('broken.ts', 'class Broken { constructor(')
        self.write('valid.ts', 'const data: any = 0;')
        report = self.run_review(['broken.ts', 'valid.ts'])
        self.assertEqual(report['exitCode'], 1)
        self.assertTrue(any(r['path'] == 'valid.ts' and r['ruleId'] == 'TYPE.EXPLICIT_ANY' for r in report['results']))

    def test_profile_visibility_includes_parameter_properties(self):
        self.write('a.ts', 'class Model { constructor(readonly value: string) {} }')
        report = self.run_review(['a.ts'], profile={'explicitPublic': True})
        self.assertEqual(sum(r['ruleId'] == 'MEMBER.VISIBILITY' for r in report['results']), 2)

    def test_symbol_reference_and_index_only_keys(self):
        self.write('a.ts', 'export {}; const item: {title: string} = {title:"x"}; console.log(item["title"]); const data: Record<string,string> = {}; console.log(data["key"], data["99"]); function run(arg) { return arg; }')
        report = self.run_review(['a.ts'], ['--depth', 'semantic'], {'compilerOptions': {'noPropertyAccessFromIndexSignature': True, 'target': 'ES2022'}})
        self.assertEqual(sum(r['ruleId'] == 'TYPE.DOT_CANDIDATE' for r in report['results']), 1)
        self.assertTrue(any(r['ruleId'] == 'TYPE.INFERRED_ANY' for r in report['results']))

    def test_missing_dependency_is_not_semantic_pass(self):
        self.write('a.ts', 'import { missing } from "./absent"; export const value = missing();')
        report = self.run_review(['a.ts'], ['--depth', 'semantic'])
        self.assertEqual(next(r for r in report['results'] if r['ruleId'] == 'TYPE.COVERAGE')['status'], 'SKIP')

    def test_approved_dependency_is_read_not_report_scope(self):
        self.write('a.ts', 'import {value} from "./dep"; export const result = value;')
        self.write('dep.ts', 'export const value: any = 1;')
        report = self.run_review(['a.ts'], ['--depth', 'semantic', '--dependency', 'dep.ts'])
        self.assertIn('dep.ts', report['inputs'])
        self.assertFalse(any(r['path'] == 'dep.ts' for r in report['results']))

    def test_missing_typescript_and_html_continue_independently(self):
        self.write('a.ts', 'export const value = 1;')
        self.write('a.html', '<p>{{ value }}</p>')
        report = self.run_review(['a.ts', 'a.html'], ['--typescript', str(self.home / 'absent.cjs')])
        self.assertEqual(report['exitCode'], 2)
        self.assertTrue(any(r['ruleId'] == 'HTML.PARSE' and r['status'] == 'SKIP' for r in report['results']))

    def test_runtime_does_not_execute_target(self):
        self.write('a.ts', 'throw new Error("do not execute");')
        report = self.run_review(['a.ts'], ['--depth', 'runtime'])
        self.assertFalse(report['coverage']['runtimeExecuted'])
        self.assertTrue(any(r['ruleId'] == 'PERF.RUNTIME' and r['status'] == 'SKIP' for r in report['results']))

    def test_scope_escape_fails_closed(self):
        self.write('a.ts', '')
        report = self.run_review(['a.ts'], ['--scope', '../'])
        self.assertEqual(report['exitCode'], 2)
        self.assertNotIn('coverage', report)

    def test_report_overwrite_is_rejected(self):
        self.write('a.ts', '')
        self.run_review(['a.ts'])
        original = self.report.read_bytes()
        command = [sys.executable, str(SCRIPT), '--root', str(self.root), '--scope', '.', '--mode', 'module',
                   '--typescript', os.environ['TYPESCRIPT_PATH'], '--report', str(self.report)]
        self.assertEqual(subprocess.run(command, capture_output=True).returncode, 2)
        self.assertEqual(original, self.report.read_bytes())

    def test_selected_cycle_is_candidate_not_runtime_failure(self):
        self.write('a.ts', 'import type {B} from "./b"; export interface A { b?: B; }')
        self.write('b.ts', 'import type {A} from "./a"; export interface B { a?: A; }')
        report = self.run_review(['a.ts', 'b.ts'], ['--depth', 'semantic'])
        self.assertTrue(any(r['ruleId'] == 'IMPORT.CYCLE' and r['status'] == 'WARN' for r in report['results']))

    def test_formatter_noop_is_pass(self):
        self.write('a.ts', 'const value = 1;\n')
        report = self.run_review(['a.ts'], profile={'format': {'indentSize': 2, 'semicolons': 'insert'}})
        self.assertEqual(next(r for r in report['results'] if r['ruleId'] == 'FORMAT.EFFECTIVE')['status'], 'PASS')

    def test_diff_literal_scope_never_scans_sibling(self):
        self.write('selected/a.ts', 'const value = 1;')
        self.write('sibling/secret.ts', 'const value: any = 1;')
        subprocess.run(['git', 'init', '-q', str(self.root)], check=True, capture_output=True)
        args = [sys.executable, '-B', str(SCRIPT), '--root', str(self.root), '--scope', 'selected', '--mode', 'diff',
                '--untracked', '--typescript', os.environ['TYPESCRIPT_PATH'], '--report', str(self.report)]
        run = subprocess.run(args, capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        report = json.loads(self.report.read_text())
        self.assertEqual(list(report['inputs']), ['selected/a.ts'])

    def test_module_selection_excludes_dependencies_and_outputs(self):
        self.write('a.ts', 'export {};')
        self.write('node_modules/secret.ts', 'const hidden: any = 1;')
        self.write('dist/output.ts', 'const hidden: any = 1;')
        args = [sys.executable, '-B', str(SCRIPT), '--root', str(self.root), '--scope', '.', '--mode', 'module',
                '--typescript', os.environ['TYPESCRIPT_PATH'], '--report', str(self.report)]
        self.assertEqual(subprocess.run(args, capture_output=True).returncode, 0)
        self.assertEqual(list(json.loads(self.report.read_text())['inputs']), ['a.ts'])

    def test_stale_snapshot_detected_without_executing_target(self):
        target = self.write('a.ts', 'export {};')
        # Mock only the worker boundary; the runner must invalidate its receipt.
        from unittest.mock import patch
        def changed(*args, **kwargs):
            target.write_text('export const changed = true;')
            return subprocess.CompletedProcess([], 0, json.dumps({'results': []}), '')
        argv = ['--root', str(self.root), '--scope', '.', '--mode', 'files', '--file', 'a.ts',
                '--typescript', os.environ['TYPESCRIPT_PATH'], '--report', str(self.report)]
        with patch.object(module, 'command', changed):
            self.assertEqual(module.main(argv), 2)
        self.assertFalse(json.loads(self.report.read_text()).get('inputsUnchanged', False))

    @unittest.skipUnless(os.environ.get('ANGULAR_COMPILER_PATH'), 'Optional approved Angular compiler required')
    def test_template_ast_any_and_dynamic_event_are_candidates(self):
        self.write('a.html', '<button (click)="open()">{{ $any(value).name }}</button>')
        report = self.run_review(['a.html'], ['--angular-compiler', os.environ['ANGULAR_COMPILER_PATH']])
        self.assertTrue(any(r['ruleId'] == 'HTML.ANY' for r in report['results']))
        self.assertTrue(any(r['ruleId'] == 'PERF.TEMPLATE_CALL' for r in report['results']))
        self.assertFalse(report['coverage']['templateTypeCheck'])


if __name__ == '__main__':
    unittest.main()
