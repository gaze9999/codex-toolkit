// angular-component-test runner checks. End-to-end cases need an installed Angular project and Chrome or Edge:
//   ANGULAR_PROJECT=<project root> [ANGULAR_TSCONFIG=<tsconfig to extend>] node --test mcp/tests/test_angular_component_test.mjs
// Without them those cases are skipped, which is not a pass. Suites are synthetic fixtures; the project is never modified.
import test from 'node:test';
import assert from 'node:assert/strict';
import { chmodSync, cpSync, existsSync, mkdirSync, mkdtempSync, readdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const skill = path.resolve(here, '../../skills/angular-component-test');
const fixtures = path.join(here, 'fixtures/angular-component-test');
const { aliasTargets, emitted, loadEsbuild } = await import(path.join(skill, 'scripts/lib/build.mjs'));
const { findBrowser } = await import(path.join(skill, 'scripts/lib/chrome.mjs'));
const { atLeast, findRenderer, renderHtml, reportData } = await import(path.join(skill, 'scripts/lib/html.mjs'));
const { exitCode, LIMITS, parseFormats, renderMarkdown, REPORT_SCHEMA, startedAtText, summarize, versionRows } = await import(path.join(skill, 'scripts/lib/report.mjs'));
const { main, packageVersions, parseArgs, readMeta, WORK_PREFIX } = await import(path.join(skill, 'scripts/run.mjs'));

const project = process.env.ANGULAR_PROJECT ? path.resolve(process.env.ANGULAR_PROJECT) : null;
const baseConfig = project && (process.env.ANGULAR_TSCONFIG ? path.resolve(process.env.ANGULAR_TSCONFIG)
  : ['tsconfig.base.json', 'tsconfig.json'].map(name => path.join(project, name)).find(file => existsSync(file)));
const browser = (() => { try { return findBrowser(); } catch { return null; } })();
const renderer = (() => { try { return findRenderer(); } catch { return null; } })();
const required = ['--project', '/p', '--tsconfig', '/t.json', '--suite', '/s', '--out', '/o'];

test('arguments require the four paths, a contained .ts entry and a report folder outside the suite', () => {
  assert.throws(() => parseArgs(['--project', '/p']), /--tsconfig/);
  assert.equal(parseArgs(required).entry, 'suite.ts');
  assert.equal(parseArgs(required).timezone, 'UTC');
  assert.throws(() => parseArgs([...required, '--entry', '../outside.ts']), /--entry/);
  assert.throws(() => parseArgs([...required, '--entry', 'suite.js']), /--entry/);
  assert.throws(() => parseArgs([...required, '--timeout', '0']), /--timeout/);
  assert.equal(parseArgs([...required, '--case-timeout', '2']).caseTimeoutMs, 2000);
  assert.throws(() => parseArgs(['--project', '/p', '--tsconfig', '/t.json', '--suite', '/s', '--out', '/s/report']), /--out/);
});

test('a configuration error exits 3 and help exits 0', async () => {
  assert.equal(await main(['--project', '/p']), 3);
  assert.equal(await main(['--help']), 0);
});

test('aliases resolve exact and wildcard keys in order', () => {
  const paths = { '@acme/shared': ['/w/libs/shared/index.ts'], '@project/*': ['/w/*'], 'pre*fix': ['/a/*', '/b/*'] };
  assert.deepEqual(aliasTargets(paths, '@acme/shared'), ['/w/libs/shared/index.ts']);
  assert.deepEqual(aliasTargets(paths, '@project/src/app/x'), ['/w/src/app/x']);
  assert.deepEqual(aliasTargets(paths, 'pre-mid-fix'), ['/a/-mid-', '/b/-mid-']);
  assert.equal(aliasTargets(paths, '@acme/shared/deep'), null);
  assert.equal(aliasTargets(paths, '@angular/core'), null);
});

test('emitted output mirrors the absolute source path, file before index', t => {
  const out = mkdtempSync(path.join(os.tmpdir(), 'component-test-emit-'));
  t.after(() => rmSync(out, { recursive: true, force: true }));
  const source = path.join(path.parse(out).root, 'src', 'feature.ts');
  const mirror = path.join(out, path.relative(path.parse(source).root, path.dirname(source)));
  assert.equal(emitted(out, source), null);
  mkdirSync(path.join(mirror, 'feature'), { recursive: true });
  writeFileSync(path.join(mirror, 'feature', 'index.js'), '');
  assert.equal(emitted(out, source), path.join(mirror, 'feature', 'index.js'));
  writeFileSync(path.join(mirror, 'feature.js'), '');
  assert.equal(emitted(out, source), path.join(mirror, 'feature.js'));
});

test('a project without esbuild or an Angular builder is a configuration error', t => {
  const empty = mkdtempSync(path.join(os.tmpdir(), 'component-test-empty-'));
  t.after(() => rmSync(empty, { recursive: true, force: true }));
  writeFileSync(path.join(empty, 'package.json'), '{}');
  assert.throws(() => loadEsbuild(empty), /esbuild/);
});

test('exit codes never pass when nothing was judged', () => {
  assert.equal(exitCode(summarize([])), 2);
  assert.equal(exitCode(summarize([{ status: 'info' }])), 2);
  assert.equal(exitCode(summarize([{ status: 'passed' }, { status: 'info' }])), 0);
  assert.equal(exitCode(summarize([{ status: 'passed' }, { status: 'failed' }])), 1);
  assert.equal(exitCode(summarize([{ status: 'error' }])), 1);
});

const sample = () => ({
  tool: { name: 'angular-component-test', version: 't' }, statusText: 's', exitCode: 1, startedAt: 'now', runtime: { node: 'v', browser: 'b', timezone: 'UTC' },
  sources: { project: { root: '/p', revision: 'r', dirty: [] }, tsconfig: '/t', suite: { root: '/s', entry: 'suite.ts', files: [] } },
  summary: summarize([{ status: 'failed' }]), consoleErrors: ['<script>x</script>'], limits: LIMITS, renderer: { name: 'report-html', version: '0.1.0' },
  results: [{ id: 'X1', group: 'g', name: 'a|b<i>', status: 'failed', assertions: [{ label: 'v', pass: false, actual: 'x|y', expected: 'z' }] }],
});

test('formats default to all three and reject unknown names', () => {
  assert.deepEqual(parseFormats(undefined), ['html', 'md', 'json']);
  assert.deepEqual(parseFormats('html'), ['html']);
  assert.deepEqual(parseFormats('json,md,json'), ['json', 'md']);
  assert.throws(() => parseFormats('pdf'), /--format/);
});

test('markdown escapes table cells', () => {
  const text = renderMarkdown(sample());
  assert.match(text, /a\\\|b/);
  assert.match(text, /❌ 不通過/);
  assert.match(text, /## 證據範圍/);
  assert.match(text, /HTML 產生器 \| report-html 0\.1\.0/);
});

test('start time shows in the page time zone and the time zone row is gone', () => {
  const model = { ...sample(), startedAt: '2026-11-17T09:08:46.214Z', runtime: { node: 'v', browser: 'b', timezone: 'Asia/Taipei' } };
  assert.equal(startedAtText(model), '2026-11-17 17:08:46 (Asia/Taipei)');
  assert.equal(startedAtText({ ...model, runtime: { ...model.runtime, timezone: null }, requestedTimezone: 'UTC' }), '2026-11-17 09:08:46 (UTC)');
  assert.equal(startedAtText({ ...model, runtime: { ...model.runtime, timezone: 'Not/AZone' } }), '2026-11-17T09:08:46.214Z');
  const keys = versionRows(model).map(([key]) => key);
  assert.ok(!keys.includes('時區'));
  assert.ok(keys.includes('執行時間'));
});

test('branch, package versions and supplied environment rows appear only when present', t => {
  const model = sample();
  model.sources.project = { root: '/p', revision: 'r', branch: 'feature/x', dirty: [], packages: [{ name: '@angular/core', version: '19.2.0' }] };
  model.environment = [['資料庫', 'PostgreSQL 16'], ['後端版本', '1.2.3']];
  const rows = Object.fromEntries(versionRows(model));
  assert.equal(rows['專案版本'], 'r, 分支 feature/x, 未提交檔案 0 個');
  assert.equal(rows['相依套件版本'], '@angular/core 19.2.0');
  assert.equal(rows['資料庫'], 'PostgreSQL 16');
  const bare = Object.fromEntries(versionRows(sample()));
  assert.equal(bare['專案版本'], 'r, 未提交檔案 0 個');
  assert.ok(!('相依套件版本' in bare));
  const temp = mkdtempSync(path.join(os.tmpdir(), 'component-test-meta-'));
  t.after(() => rmSync(temp, { recursive: true, force: true }));
  const file = path.join(temp, 'meta.json');
  writeFileSync(file, JSON.stringify({ 資料庫: 'PostgreSQL 16', 筆數: 3 }));
  assert.deepEqual(readMeta(file), [['資料庫', 'PostgreSQL 16'], ['筆數', '3']]);
  writeFileSync(file, JSON.stringify(['x']));
  assert.throws(() => readMeta(file), /物件/);
  writeFileSync(file, JSON.stringify({ 巢狀: { a: 1 } }));
  assert.throws(() => readMeta(file), /巢狀/);
  mkdirSync(path.join(temp, 'node_modules', 'rxjs'), { recursive: true });
  writeFileSync(path.join(temp, 'node_modules', 'rxjs', 'package.json'), JSON.stringify({ version: '7.8.1' }));
  assert.deepEqual(packageVersions(temp), [{ name: 'rxjs', version: '7.8.1' }]);
});

test('the report schema is a named version string', () => {
  assert.equal(REPORT_SCHEMA, 'angular-component-test-report/1');
});

test('report-html/v1 data maps status, counts, group cards, filters and every case', () => {
  const data = reportData(sample());
  assert.equal(data.schema, 'report-html/v1');
  assert.deepEqual(data.tags, [{ label: 's', tone: 'error' }]);
  assert.deepEqual(data.stats.map(stat => [stat.label, stat.value, stat.section]), [['通過', 0, 0], ['不通過', 1, 0], ['錯誤', 0, 0], ['觀察', 0, 0], ['合計', 1, 0]]);
  assert.deepEqual(data.panels.map(panel => [panel.label, panel.kind]), [['測試判定', 'cards']]);
  assert.deepEqual(data.panels[0].items, [{ value: '0 / 1', label: 'g', note: '不通過或錯誤 1', tone: 'error', title: '❌ 不通過 X1 a|b<i>' }]);
  assert.deepEqual(data.sections.map(section => [section.label, section.kind ?? 'table']), [['案例結果', 'table'], ['瀏覽器錯誤訊息', 'list'], ['證據範圍', 'list']]);
  assert.deepEqual(data.sections[0].filters.map(filter => filter.key), ['status', 'group']);
  assert.equal(data.sections[0].rows[0].verdict, '✗ v: 實際 "x|y", 預期 "z"');
  assert.deepEqual(reportData({ ...sample(), error: 'boom' }).panels[0], { label: '設定或編譯錯誤', kind: 'text', text: 'boom' });
});

test('renderer versions below 0.2.0 cannot read report-html/v1', () => {
  assert.equal(atLeast('0.2.0', '0.2.0'), true);
  assert.equal(atLeast('0.10.1', '0.2.0'), true);
  assert.equal(atLeast('0.1.9', '0.2.0'), false);
});

const fakeRenderer = (t, renderBody) => {
  const dir = mkdtempSync(path.join(os.tmpdir(), 'component-test-renderer-'));
  t.after(() => rmSync(dir, { recursive: true, force: true }));
  const file = path.join(dir, 'report-html');
  writeFileSync(file, `#!/bin/sh\nif [ "$1" = "--version" ]; then echo "report-html 9.9.9"; exit 0; fi\ncat >/dev/null\n${renderBody}\n`);
  chmodSync(file, 0o755);
  return file;
};

test('a missing renderer is a configuration error that still writes JSON and Markdown', async t => {
  const out = mkdtempSync(path.join(os.tmpdir(), 'component-test-norender-'));
  t.after(() => rmSync(out, { recursive: true, force: true }));
  assert.throws(() => findRenderer(undefined, { PATH: '' }), /report-html/);
  assert.equal(await main(['--project', '/p', '--tsconfig', '/t.json', '--suite', '/s', '--out', out, '--report-html', path.join(out, 'none')]), 3);
  assert.deepEqual(readdirSync(out).sort(), ['report.json', 'report.md']);
});

test('a failed render keeps JSON and Markdown and exits 3', { skip: process.platform === 'win32' ? 'shell stand-in' : false }, async t => {
  const out = mkdtempSync(path.join(os.tmpdir(), 'component-test-badrender-'));
  t.after(() => rmSync(out, { recursive: true, force: true }));
  const code = await main(['--project', '/p', '--tsconfig', '/t.json', '--suite', '/s', '--out', out, '--report-html', fakeRenderer(t, 'echo broken >&2; exit 2')]);
  assert.equal(code, 3);
  assert.deepEqual(readdirSync(out).sort(), ['report.json', 'report.md']);
  const report = JSON.parse(readFileSync(path.join(out, 'report.json'), 'utf8'));
  assert.match(report.error, /report-html 產生失敗[\s\S]*broken/);
  assert.equal(report.renderer.version, '9.9.9');
  assert.equal(report.renderer.schema, 'report-html/v1');
});

test('an installed renderer older than 0.2.0 is a configuration error', { skip: process.platform === 'win32' ? 'shell stand-in' : false }, t => {
  const old = fakeRenderer(t, 'exit 0').replace(/report-html$/, 'old-report-html');
  writeFileSync(old, '#!/bin/sh\necho "report-html 0.1.0"\n');
  chmodSync(old, 0o755);
  assert.throws(() => findRenderer(old), /0\.1\.0 不支援 report-html\/v1/);
});

test('the installed report-html renders an escaped offline page', { skip: renderer ? false : 'report-html 0.2.0 or newer is not available' }, () => {
  const html = renderHtml(sample(), renderer);
  assert.match(html, /^<!doctype html>/);
  assert.match(html, /a\|b&lt;i&gt;/);
  assert.match(html, /&lt;script&gt;x&lt;\/script&gt;/);
  assert.doesNotMatch(html, /<script src=|<link /);
  assert.match(html, /<select/);
});

test('distributed sources carry no project-specific names', () => {
  const files = [];
  const visit = dir => { for (const entry of readdirSync(dir, { withFileTypes: true })) (entry.isDirectory() ? visit : file => files.push(file))(path.join(dir, entry.name)); };
  visit(skill);
  visit(fixtures);
  for (const file of files.filter(name => /\.(mjs|ts|md|yaml)$/.test(name)))
    assert.doesNotMatch(readFileSync(file, 'utf8'), /sfap|@web\/|ScpHttp|Sacrm|wbui|spec-verify/i, file);
});

const workFolders = () => readdirSync(os.tmpdir()).filter(name => name.startsWith(WORK_PREFIX)).length;

const runSuite = async (t, suite, extra = []) => {
  const temp = mkdtempSync(path.join(os.tmpdir(), 'component-test-case-'));
  t.after(() => rmSync(temp, { recursive: true, force: true }));
  const tsconfig = path.join(temp, 'tsconfig.json');
  writeFileSync(tsconfig, JSON.stringify({
    extends: baseConfig, compilerOptions: { target: 'es2022', strict: true }, angularCompilerOptions: { strictTemplates: true },
  }));
  const out = path.join(temp, 'report');
  const before = workFolders();
  const code = await main(['--project', project, '--tsconfig', tsconfig, '--suite', suite, '--out', out, '--timezone', 'Asia/Taipei', ...extra]);
  assert.equal(workFolders(), before, 'work folder removed');
  assert.ok(existsSync(path.join(project, 'node_modules', '@angular', 'core', 'package.json')), 'project dependencies untouched');
  const read = name => (existsSync(path.join(out, name)) ? readFileSync(path.join(out, name), 'utf8') : null);
  return { code, out, report: read('report.json') && JSON.parse(read('report.json')), markdown: read('report.md'), html: read('report.html') };
};

const e2e = { skip: !project ? 'ANGULAR_PROJECT is not set' : !baseConfig ? 'no tsconfig to extend' : !browser ? 'Chrome or Edge is not installed' : !renderer ? 'report-html 0.2.0 or newer is not available' : false };

test('a mixed suite reports passed, failed, error and observation cases in order', e2e, async t => {
  const { code, report, markdown, html } = await runSuite(t, path.join(fixtures, 'basic'));
  assert.equal(code, 1);
  assert.deepEqual(report.results.map(result => [result.id, result.status]), [['F1', 'passed'], ['F2', 'failed'], ['F3', 'error'], ['O1', 'info']]);
  assert.deepEqual(report.results.find(result => result.id === 'O1').observed, { timezone: 'Asia/Taipei', epochDay: 1 });
  assert.match(report.results.find(result => result.id === 'F3').message, /fixture error/);
  assert.equal(report.sources.suite.files.length, 2);
  assert.match(report.runtime.browser, /Chrome|Edg/);
  assert.match(report.runtime.userAgent, /^Mozilla\/5\.0 .*(Chrome|Edg)\//);
  assert.match(markdown, /\| User Agent \| Mozilla\/5\.0 /);
  assert.match(html, /User Agent/);
  assert.equal(report.runtime.timezone, 'Asia/Taipei');
  assert.match(markdown, /\| 執行時間 \| \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} \(Asia\/Taipei\) \|/);
  assert.doesNotMatch(markdown, /\| 時區 \|/);
  assert.ok(report.sources.project.packages.some(item => item.name === '@angular/core'));
  assert.equal(report.schemaVersion, 'angular-component-test-report/1');
  assert.match(markdown, /❌ 錯誤/);
  assert.match(html, /F2/);
});

test('--format html writes only report.html with the title', e2e, async t => {
  const { code, out, html } = await runSuite(t, path.join(fixtures, 'basic'), ['--entry', 'passing.ts', '--format', 'html', '--title', '合成報告']);
  assert.equal(code, 0);
  assert.deepEqual(readdirSync(out), ['report.html']);
  assert.match(html, /<title>合成報告<\/title>/);
  assert.match(html, /P1/);
});

test('a passing entry exits 0', e2e, async t => {
  const { code, report } = await runSuite(t, path.join(fixtures, 'basic'), ['--entry', 'passing.ts']);
  assert.equal(code, 0);
  assert.deepEqual(report.summary, { total: 1, passed: 1, failed: 0, error: 0, info: 0 });
});

test('a type error stops before the browser with exit 3', e2e, async t => {
  const { code, report } = await runSuite(t, path.join(fixtures, 'broken'));
  assert.equal(code, 3);
  assert.match(report.error, /ngc/);
  assert.equal(report.runtime.browser, null);
  assert.equal(report.runtime.userAgent, null);
  assert.equal(report.runtime.timezone, null);
});

test('the suite template compiles and runs as written', e2e, async t => {
  const suite = mkdtempSync(path.join(os.tmpdir(), 'component-test-template-'));
  t.after(() => rmSync(suite, { recursive: true, force: true }));
  cpSync(path.join(skill, 'assets/suite.template.ts'), path.join(suite, 'suite.ts'));
  const { code, report } = await runSuite(t, suite);
  assert.equal(code, 0, report.error);
  assert.deepEqual(report.results.map(result => [result.id, result.status]), [['X-1', 'passed'], ['X-2', 'info']]);
});
