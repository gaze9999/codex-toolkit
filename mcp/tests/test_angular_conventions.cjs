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
