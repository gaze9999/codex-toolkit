'use strict';
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const { spawnSync } = require('node:child_process');
const root = path.resolve(__dirname, '../..');
const checker = path.join(root, 'skills/angular-development/scripts/check_conventions.cjs');
const { loadTypeScript, checkSource } = require(checker);
// Point at an existing compatible project or TypeScript module; never install one for this suite
const ts = loadTypeScript({ project: process.env.ANGULAR_TEST_PROJECT || root, typescript: process.env.TYPESCRIPT_PATH });
const check = (text, filename = 'example.ts') => checkSource(ts, text, filename);

test('readonly constructor properties in an Error model are checked with constructors', () => {
  const rows = check('class LookupError extends Error { constructor(readonly operation: string, readonly cause: unknown) { super(operation); } }');
  assert.deepEqual(rows.map(row => [row.kind, row.name]), [
    ['constructor', 'constructor'], ['parameter-property', 'operation'], ['parameter-property', 'cause'],
  ]);
});
test('public visibility keeps readonly and emits the same JavaScript', () => {
  const before = 'class Failure { constructor(readonly code: string) {} }';
  const after = 'class Failure { public constructor(public readonly code: string) {} }';
  assert.equal(check(after).length, 0);
  assert.equal(ts.transpileModule(before, {}).outputText, ts.transpileModule(after, {}).outputText);
});
test('private, protected, hash-private, interfaces and ordinary parameters are excluded', () => {
  assert.deepEqual(check('interface View { value: string; show(): void; } class Task { #value = 1; private constructor(private readonly id: string, protected scope: string, input: number) {} protected read() {} }'), []);
});
test('properties, methods, accessors, overloads and static members are checked', () => {
  const rows = check('class Task { static count = 0; value = 1; get title() { return ""; } set title(value: string) {} run(x: string): void; run(x: unknown) {} }');
  assert.deepEqual(rows.map(row => row.name), ['count', 'value', 'title', 'title', 'run', 'run']);
});
test('class expressions and nested classes are included', () => {
  assert.deepEqual(check('const Task = class { run() { class Inner { value = 1; } } };').map(row => row.name), ['run', 'value']);
});
test('declaration files are skipped and string/type syntax remains intact', () => {
  assert.deepEqual(check('declare class External { value: undefined; constructor(value: string); }', 'external.d.ts'), []);
  assert.deepEqual(check('class Task { public value: string | undefined; public readonly label = "undefined"; public run(input: undefined) { return void 0; } }'), []);
});
test('parse failures do not report a pass', () => {
  assert.throws(() => check('class Broken { public constructor('), /example.ts:/);
});
test('findings include exact one-based location', () => {
  const [row] = check('class Task {\n  value = 1;\n}');
  assert.equal(row.line, 2);
  assert.equal(row.column, 3);
});
test('CLI is opt-in, rejects invalid scope and leaves input bytes unchanged', () => {
  const temporary = fs.mkdtempSync(path.join(os.tmpdir(), 'angular-conventions-'));
  const file = path.join(temporary, 'fixture.ts');
  const original = Buffer.from('class Task { constructor(readonly code: string) {} }');
  fs.writeFileSync(file, original);
  const typescript = process.env.TYPESCRIPT_PATH || require.resolve('typescript', { paths: [process.env.ANGULAR_TEST_PROJECT || root] });
  const run = args => spawnSync(process.execPath, [checker, ...args], { encoding: 'utf8' });
  try {
    const missingConvention = run(['--typescript', typescript, file]);
    assert.equal(missingConvention.status, 2);
    const found = run(['--explicit-public', '--typescript', typescript, file]);
    assert.equal(found.status, 1, found.stderr);
    assert.equal(JSON.parse(found.stdout).findings.length, 2);
    assert.deepEqual(fs.readFileSync(file), original);
    assert.equal(run(['--explicit-public', '--typescript', typescript, temporary]).status, 2);
    assert.equal(run(['--explicit-public', '--project', temporary, file]).status, 2);
    assert.equal(run(['--typescript']).status, 2);
    fs.writeFileSync(file, original.toString().replace('constructor(readonly', 'public constructor(public readonly'));
    const normalized = fs.readFileSync(file);
    assert.equal(run(['--explicit-public', '--typescript', typescript, file]).status, 0);
    assert.deepEqual(fs.readFileSync(file), normalized);
    fs.writeFileSync(file, original);
    assert.deepEqual(fs.readFileSync(file), original);
  } finally {
    fs.unlinkSync(file);
    fs.rmdirSync(temporary);
  }
});

test('Git discovery scopes staged, unstaged and untracked files and reports working-tree evidence', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'angular-scope-'));
  const git = args => { const r = spawnSync('git', ['-C', dir, ...args], { encoding: 'utf8' }); assert.equal(r.status, 0, r.stderr); return r.stdout; };
  const typescript = process.env.TYPESCRIPT_PATH || require.resolve('typescript', { paths: [process.env.ANGULAR_TEST_PROJECT || root] });
  const run = args => spawnSync(process.execPath, [checker, '--typescript', typescript, ...args], { encoding: 'utf8' });
  try {
    git(['init']); fs.mkdirSync(path.join(dir, 'feature'));
    fs.writeFileSync(path.join(dir, 'feature', 'tracked.ts'), 'export const value = 1;\n');
    fs.writeFileSync(path.join(dir, 'outside.ts'), 'const ignored=1');
    git(['add', '.']); git(['-c','user.name=Fixture','-c','user.email=fixture@example.invalid','commit','-m','fixture']);
    fs.writeFileSync(path.join(dir, 'feature', 'tracked.ts'), 'export const value = 2;\n');
    git(['add', 'feature/tracked.ts']);
    fs.appendFileSync(path.join(dir, 'feature', 'tracked.ts'), 'export const next = 3;\n');
    fs.writeFileSync(path.join(dir, 'feature', 'new file.ts'), 'export const added=1');
    fs.writeFileSync(path.join(dir, 'feature', 'view.html'), '<div></div>');
    fs.appendFileSync(path.join(dir, 'outside.ts'), '\nconst other=2');
    const report = path.join(dir, 'result.json');
    const args = ['--git-root',dir,'--scope','feature','--staged','--unstaged','--untracked','--format','--indent-size','2','--semicolons','insert'];
    const r = run([...args,'--report',report]); assert.equal(r.status,1,r.stderr);
    const out = JSON.parse(r.stdout); assert.equal(out.files,2); assert.equal(out.skipped.length,1);
    assert.equal(out.formatting.length,1); assert.equal(out.checks.memberOrder,'not-run'); assert.equal(out.checks.explicitPublic,'not-run');
    assert.equal(out.inputs[0].sha256.length,64); assert.equal(fs.readFileSync(report,'utf8'),r.stdout);
    assert.equal(fs.readFileSync(path.join(dir,'feature','new file.ts'),'utf8'),'export const added=1');
    assert.equal(run([...args,'--report',report]).status,2);
    assert.equal(run(['--explicit-public','--git-root',dir,'--scope','../','--untracked']).status,2);
    const empty=run(['--explicit-public','--git-root',dir,'--scope','missing','--unstaged']);
    assert.equal(JSON.parse(empty.stdout).status,'no-files');
    assert.equal(JSON.parse(empty.stdout).checks.syntax,'not-run');
    const staged=run(['--explicit-public','--git-root',dir,'--scope','feature','--staged']);
    assert.equal(JSON.parse(staged.stdout).files,1);
  } finally { fs.rmSync(dir,{recursive:true,force:true}); }
});

test('formatter preserves literals, CRLF and repeated output', () => {
  const { formatSource } = require(checker);
  const source='export const text="keep  two spaces";\r\n';
  const options={indentSize:2,semicolons:'insert'};
  const result=formatSource(ts,source,'fixture.ts',options);
  assert(result.includes('keep  two spaces')); assert(result.includes('\r\n'));
  assert.equal(formatSource(ts,result,'fixture.ts',options),result);
});
