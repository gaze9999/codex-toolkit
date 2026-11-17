// Angular component tests: AOT-compile a suite against the real components, run it in headless Chrome or Edge and write report.html, report.md and report.json.
// Usage:
//   node run.mjs --project <Angular project root> --tsconfig <tsconfig.json> --suite <suite folder> --out <output folder>
//                [--entry suite.ts] [--format html,md,json] [--title <text>] [--chrome <browser>] [--report-html <cli>] [--meta-file <json>] [--timezone UTC] [--timeout 300] [--case-timeout 15] [--keep-work]
// HTML is rendered by the shared report-html CLI from report-html/v1 data; Markdown and JSON need no extra tool.
// The suite imports @component-test/harness for test(), mount() and DOM helpers, and @project/<path> for project sources.
// Exit codes: 0 every judged case passed, 1 a case failed or errored, 2 nothing was judged, 3 configuration or compile error.
import { spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { cpSync, existsSync, mkdirSync, mkdtempSync, readFileSync, realpathSync, rmSync, statSync, writeFileSync } from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { buildPage, copySuite } from './lib/build.mjs';
import { findBrowser, runPage } from './lib/chrome.mjs';
import { findRenderer, HTML_SCHEMA, renderHtml } from './lib/html.mjs';
import { exitCode, LIMITS, parseFormats, renderMarkdown, REPORT_SCHEMA, summarize, TOOL_NAME, TOOL_VERSION } from './lib/report.mjs';

const here = path.dirname(fileURLToPath(import.meta.url));
const hash = data => createHash('sha256').update(data).digest('hex');
export const WORK_PREFIX = `${TOOL_NAME}-`;
const HELP = `用法: node run.mjs --project <Angular 專案> --tsconfig <tsconfig.json> --suite <套件資料夾> --out <報告資料夾>
選用: --entry suite.ts --format html,md,json --title <標題> --chrome <瀏覽器> --report-html <CLI> --meta-file <環境資訊 JSON> --timezone UTC --timeout 300 --case-timeout 15 --keep-work
結束碼: 0 全部通過, 1 有案例不通過或錯誤, 2 沒有可判定的案例, 3 設定或編譯錯誤`;

export function parseArgs(argv) {
  const args = Object.fromEntries(argv.reduce((pairs, token, i, all) => {
    if (token.startsWith('--')) pairs.push([token.slice(2), all[i + 1] && !all[i + 1].startsWith('--') ? all[i + 1] : true]);
    return pairs;
  }, []));
  for (const key of ['project', 'tsconfig', 'suite', 'out']) if (!args[key] || args[key] === true) throw new Error(`需要 --${key}`);
  for (const key of ['project', 'tsconfig', 'suite', 'out', 'chrome', 'report-html', 'meta-file']) if (typeof args[key] === 'string') args[key] = path.resolve(args[key]);
  const seconds = (key, fallback, max) => {
    const value = args[key] === undefined ? fallback : Number(args[key]);
    if (!Number.isFinite(value) || value <= 0 || value > max) throw new Error(`--${key} 需為 1 到 ${max} 秒`);
    return value * 1000;
  };
  const entry = typeof args.entry === 'string' ? args.entry : 'suite.ts';
  if (path.isAbsolute(entry) || entry.split(/[\\/]/).includes('..') || !entry.endsWith('.ts')) throw new Error('--entry 需為套件資料夾內的 .ts 相對路徑');
  const out = args.out, suite = args.suite;
  if (out === suite || out.startsWith(suite + path.sep)) throw new Error('--out 不能位於 --suite 內');
  return {
    project: args.project, tsconfig: args.tsconfig, suite, out, entry, chrome: args.chrome, reportHtml: args['report-html'], metaFile: args['meta-file'], formats: parseFormats(args.format),
    title: typeof args.title === 'string' ? args.title : '元件測試報告',
    timezone: typeof args.timezone === 'string' ? args.timezone : 'UTC',
    timeoutMs: seconds('timeout', 300, 1800), caseTimeoutMs: seconds('case-timeout', 15, 600), keepWork: args['keep-work'] === true,
  };
}

/** Revision plus hashes of uncommitted tracked files, because HEAD alone misses concurrent work. */
export function projectRevision(project) {
  const git = argv => spawnSync('git', ['-C', project, ...argv], { encoding: 'utf8', maxBuffer: 16 * 1024 * 1024 });
  const head = git(['rev-parse', 'HEAD']);
  if (head.status !== 0) return { revision: null, dirty: [] };
  const top = git(['rev-parse', '--show-toplevel']).stdout.trim();
  const branch = git(['rev-parse', '--abbrev-ref', 'HEAD']).stdout.trim();
  const status = git(['status', '--porcelain=v1', '-z', '--untracked-files=no', '--', '.']).stdout;
  const dirty = status.split('\0').filter(Boolean).filter(entry => !/^R/.test(entry)).map(entry => {
    const file = entry.slice(3), full = path.join(top, file);
    return { path: file, sha256: existsSync(full) && statSync(full).isFile() ? hash(readFileSync(full)) : null };
  });
  return { revision: head.stdout.trim(), branch: branch && branch !== 'HEAD' ? branch : null, dirty };
}

/** 受測程式實際載入的框架版本, 讀取專案 node_modules, 找不到的套件不列出 */
const PACKAGES = ['@angular/core', 'typescript', 'rxjs', 'zone.js'];
export function packageVersions(project) {
  return PACKAGES.flatMap(name => {
    try {
      const { version } = JSON.parse(readFileSync(path.join(project, 'node_modules', name, 'package.json'), 'utf8'));
      return typeof version === 'string' ? [{ name, version }] : [];
    } catch {
      return [];
    }
  });
}

/** 報告附帶的環境資訊, 例如資料庫連線版本或後端版本, 由呼叫端提供 { 項目: 內容 } 物件 */
export function readMeta(file) {
  const data = JSON.parse(readFileSync(file, 'utf8'));
  if (!data || typeof data !== 'object' || Array.isArray(data)) throw new Error('需為 { "項目": "內容" } 物件');
  return Object.entries(data).map(([key, value]) => {
    if (typeof value !== 'string' && typeof value !== 'number') throw new Error(`${key} 需為字串或數字`);
    return [key, String(value)];
  });
}

export async function main(argv) {
  if (argv.includes('--help') || argv.includes('-h')) { console.log(HELP); return 0; }
  const startedAt = new Date().toISOString();
  let options;
  try { options = parseArgs(argv); } catch (error) { console.error(`設定錯誤: ${error.message}\n${HELP}`); return 3; }
  const { project, tsconfig, suite, out, entry } = options;
  const model = {
    schemaVersion: REPORT_SCHEMA, tool: { name: TOOL_NAME, version: TOOL_VERSION }, title: options.title, startedAt, requestedTimezone: options.timezone,
    runtime: { node: process.version, browser: null, userAgent: null, timezone: null },
    sources: { project: { root: project, ...projectRevision(project), packages: packageVersions(project) }, tsconfig, suite: { root: suite, entry, files: [] } },
    results: [], consoleErrors: [], limits: LIMITS, summary: summarize([]),
  };
  let renderer = null;
  const finish = (code, error) => {
    const settle = (next, message) => {
      if (message) model.error = [model.error, String(message)].filter(Boolean).join('\n').slice(0, 8000);
      model.summary = summarize(model.results);
      model.exitCode = next;
      model.statusText = { 0: '全部通過', 1: '有案例不通過或錯誤', 2: '沒有可判定的案例', 3: '設定或編譯錯誤' }[next];
    };
    settle(code, error);
    /** A failed HTML render keeps the case results in JSON and Markdown and turns the run into a configuration error. */
    let html = null;
    if (renderer) try { html = renderHtml(model, renderer); } catch (failure) { settle(3, failure.message); }
    mkdirSync(out, { recursive: true });
    const written = [];
    const write = (name, content) => { writeFileSync(path.join(out, name), content); written.push(path.join(out, name)); };
    if (options.formats.includes('json')) write('report.json', `${JSON.stringify(model, null, 2)}\n`);
    if (options.formats.includes('md')) write('report.md', renderMarkdown(model));
    if (html !== null) write('report.html', html);
    console.log(`${model.statusText}: 通過 ${model.summary.passed}, 不通過 ${model.summary.failed}, 錯誤 ${model.summary.error}, 觀察 ${model.summary.info}`);
    for (const file of written) console.log(`報告: ${file}`);
    return model.exitCode;
  };
  if (Number(process.versions.node.split('.')[0]) < 22) return finish(3, '需要 Node.js 22 以上 (使用內建 WebSocket)');
  if (options.metaFile) try { model.environment = readMeta(options.metaFile); } catch (error) { return finish(3, `--meta-file 無法使用: ${error.message}`); }
  if (options.formats.includes('html')) {
    try { renderer = findRenderer(options.reportHtml); } catch (error) { return finish(3, error.message); }
    model.renderer = { name: 'report-html', version: renderer.version, schema: HTML_SCHEMA };
  }
  for (const [key, file] of [['project', path.join(project, 'node_modules')], ['tsconfig', tsconfig], ['suite', path.join(suite, entry)]])
    if (!existsSync(file)) return finish(3, `--${key} 找不到 ${file}`);
  /** The real path keeps one module identity when the temp folder is reached through a link such as macOS /var. */
  const work = realpathSync(mkdtempSync(path.join(os.tmpdir(), WORK_PREFIX)));
  try {
    let browser, page;
    try {
      model.sources.suite.files = copySuite(suite, path.join(work, 'suite'), hash);
      cpSync(path.join(here, 'harness'), path.join(work, 'harness'), { recursive: true });
      browser = findBrowser(options.chrome);
      ({ page } = await buildPage({ project, tsconfig, work, entry, harness: path.join(work, 'harness') }));
    } catch (error) {
      return finish(3, error.message);
    }
    try {
      const run = await runPage({ browser, profile: path.join(work, 'profile'), page, timezone: options.timezone, timeoutMs: options.timeoutMs, caseTimeoutMs: options.caseTimeoutMs });
      model.runtime.browser = run.version;
      model.runtime.userAgent = run.userAgent;
      model.runtime.timezone = run.timezone;
      model.results = run.results;
      model.consoleErrors = run.consoleErrors;
    } catch (error) {
      return finish(2, error.message);
    }
    return finish(exitCode(summarize(model.results)));
  } finally {
    if (options.keepWork) console.log(`保留工作資料夾: ${work}`);
    else rmSync(work, { recursive: true, force: true, maxRetries: 5, retryDelay: 200 });
  }
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) process.exitCode = await main(process.argv.slice(2));
