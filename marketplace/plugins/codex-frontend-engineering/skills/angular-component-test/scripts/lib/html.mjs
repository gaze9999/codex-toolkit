// HTML through the shared report-html CLI: the runner maps its report model to report-html/v1 data and keeps no page layout of its own.
import { spawnSync } from 'node:child_process';
import { existsSync } from 'node:fs';
import path from 'node:path';
import { STATUS_LABELS, versionRows, verdictText } from './report.mjs';

export const HTML_SCHEMA = 'report-html/v1';
/** report-html reads report-html/v1 with panels, block kinds and table filters from this version on. */
export const MIN_RENDERER = '0.2.0';
const OVERALL_TONE = { 0: 'success', 1: 'error', 2: 'warning', 3: 'error' };
const CASES_SECTION = 0;

const versionParts = version => version.split(/[.+-]/).slice(0, 3).map(part => Number.parseInt(part, 10) || 0);
export const atLeast = (version, minimum) => {
  const [a, b] = [versionParts(version), versionParts(minimum)];
  for (let i = 0; i < 3; i++) if (a[i] !== b[i]) return a[i] > b[i];
  return !0;
};

/** report-html from --report-html, REPORT_HTML or PATH; returns its path and version, or throws with how to provide it. */
export function findRenderer(explicit, env = process.env) {
  const names = process.platform === 'win32' ? ['report-html.exe', 'report-html'] : ['report-html'];
  const chosen = explicit ?? env.REPORT_HTML
    ?? (env.PATH ?? '').split(path.delimiter).filter(Boolean).flatMap(dir => names.map(name => path.join(dir, name))).find(file => existsSync(file));
  if (!chosen) throw new Error('HTML 報告需要 report-html CLI, 請用 --report-html 或 REPORT_HTML 指定, 或改用 --format md,json');
  const probe = spawnSync(chosen, ['--version'], { encoding: 'utf8', timeout: 10000 });
  const version = probe.status === 0 ? probe.stdout.trim().match(/^report-html (\S+)$/)?.[1] : null;
  if (!version) throw new Error(`report-html 無法執行或版本無法辨識: ${chosen}`);
  if (!atLeast(version, MIN_RENDERER)) throw new Error(`report-html ${version} 不支援 ${HTML_SCHEMA}, 需要 ${MIN_RENDERER} 以上: ${chosen}`);
  return { path: chosen, version };
}

/** One card per group: passed over judged cases, an observation-only group shows its count. */
function groupCards(results) {
  return [...new Set(results.map(result => result.group))].map(name => {
    const rows = results.filter(result => result.group === name), judged = rows.filter(result => result.status !== 'info');
    const passed = judged.filter(result => result.status === 'passed').length, bad = judged.length - passed;
    const failing = rows.filter(result => result.status === 'failed' || result.status === 'error').map(result => `${STATUS_LABELS[result.status]} ${result.id} ${result.name}`);
    return {
      value: judged.length ? `${passed} / ${judged.length}` : rows.length,
      label: name || '未分組',
      note: !judged.length ? '只有觀察' : bad ? `不通過或錯誤 ${bad}` : '全部通過',
      tone: !judged.length ? 'neutral' : bad ? 'error' : 'success',
      ...(failing.length ? { title: failing.join('\n') } : {}),
    };
  });
}

/** Map the component test model to report-html/v1 data. */
export function reportData(model) {
  const { summary, results } = model;
  const stat = (label, value, tone) => ({ label, value, ...(tone ? { tone, bar: !0 } : {}), section: CASES_SECTION });
  return {
    schema: HTML_SCHEMA,
    title: model.title ?? '元件測試報告',
    lang: 'zh-Hant-TW',
    tags: [{ label: model.statusText, tone: OVERALL_TONE[model.exitCode] ?? 'warning' }],
    info: versionRows(model),
    stats: [stat('通過', summary.passed, 'success'), stat('不通過', summary.failed, 'error'), stat('錯誤', summary.error, 'error'), stat('觀察', summary.info, 'neutral'), stat('合計', summary.total)],
    panels: [
      ...(model.error ? [{ label: '設定或編譯錯誤', kind: 'text', text: model.error }] : []),
      { label: '測試判定', kind: 'cards', empty: '沒有案例', items: groupCards(results) },
    ],
    sections: [
      {
        label: '案例結果', empty: '沒有案例結果',
        filters: [{ key: 'status', label: '狀態' }, { key: 'group', label: '群組' }],
        columns: [
          { key: 'id', label: '編號' }, { key: 'group', label: '群組' }, { key: 'name', label: '案例' }, { key: 'status', label: '狀態' },
          { key: 'verdict', label: '判定' }, { key: 'observed', label: '觀察值', kind: 'code' }, { key: 'elapsed', label: '耗時 (ms)', kind: 'number' },
        ],
        rows: results.map(result => ({
          id: result.id, group: result.group, name: result.name, status: STATUS_LABELS[result.status], verdict: verdictText(result),
          observed: result.observed === undefined ? '' : JSON.stringify(result.observed), elapsed: Math.round(result.elapsedMs ?? 0),
        })),
      },
      { label: '瀏覽器錯誤訊息', kind: 'list', empty: '沒有錯誤訊息', items: model.consoleErrors },
      { label: '證據範圍', kind: 'list', items: model.limits },
    ],
    headings: { info: '版本資訊', stats: '案例狀態', sections: '明細' },
  };
}

/** Render through the CLI on stdin and return the page; stdout keeps the runner free to overwrite an earlier report.html. */
export function renderHtml(model, renderer) {
  const run = spawnSync(renderer.path, ['render', '--input', '-'], { input: JSON.stringify(reportData(model)), encoding: 'utf8', maxBuffer: 64 * 1024 * 1024, timeout: 60000 });
  if (run.status !== 0) throw new Error(`report-html 產生失敗 (${run.status ?? run.error?.message})\n${(run.stderr ?? '').trim().slice(0, 2000)}`);
  return run.stdout;
}
