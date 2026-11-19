// Report model, exit code and Markdown rendering for component test results; html.mjs renders the same model.
export const TOOL_NAME = 'angular-component-test';
export const TOOL_VERSION = '0.1.3';
export const REPORT_SCHEMA = `${TOOL_NAME}-report/v1`;
export const FORMATS = ['html', 'md', 'json'];

export const STATUS_LABELS = { passed: '✅ 通過', failed: '❌ 不通過', error: '❌ 錯誤', info: 'ℹ️ 觀察' };
export const LIMITS = [
  '輸入以程式送出 DOM 事件, 不代表原生鍵盤、貼上或輸入法行為',
  '結果只涵蓋測試套件掛載的元件與替身服務, 不代表宿主應用整合、登入、實際 API 或資料保存',
  '部分編譯的第三方套件在頁面內以 JIT 補編譯, 專案元件為 AOT',
  '元件樣式表未編譯, 測試頁版面不代表實際畫面',
];

export const parseFormats = value => {
  const formats = value && value !== true && value !== 'all' ? String(value).split(',').map(item => item.trim()) : FORMATS;
  if (!formats.length || formats.some(item => !FORMATS.includes(item))) throw new Error(`--format 只能是 ${FORMATS.join(', ')} 或 all`);
  return [...new Set(formats)];
};

export function summarize(results) {
  const counts = { total: results.length, passed: 0, failed: 0, error: 0, info: 0 };
  for (const result of results) counts[result.status] = (counts[result.status] ?? 0) + 1;
  return counts;
}

/** 0 when every judged case passed, 1 for any failure or error, 2 when nothing was judged; configuration errors use 3 in run.mjs. */
export function exitCode(summary) {
  if (summary.failed || summary.error) return 1;
  return summary.passed ? 0 : 2;
}

/** 執行時間以測試頁時區顯示, 頁面未執行時改用指定時區, 時區無效時保留 ISO 時間 */
export function startedAtText(model) {
  const timezone = model.runtime.timezone ?? model.requestedTimezone;
  const date = new Date(model.startedAt);
  if (!timezone || Number.isNaN(date.getTime())) return String(model.startedAt);
  try {
    const parts = Object.fromEntries(new Intl.DateTimeFormat('en-CA', {
      timeZone: timezone, hourCycle: 'h23', year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit',
    }).formatToParts(date).map(part => [part.type, part.value]));
    return `${parts.year}-${parts.month}-${parts.day} ${parts.hour}:${parts.minute}:${parts.second} (${timezone})`;
  } catch {
    return String(model.startedAt);
  }
}

export function versionRows(model) {
  const { sources, runtime } = model;
  const project = sources.project;
  const revision = [project.revision ?? '無法取得', project.branch && `分支 ${project.branch}`, `未提交檔案 ${project.dirty.length} 個`].filter(Boolean).join(', ');
  return [
    ['工具', `${model.tool.name} ${model.tool.version}`],
    ['結果', model.statusText],
    ['執行時間', startedAtText(model)],
    ['Node', runtime.node],
    ['瀏覽器', runtime.browser ?? '未啟動'],
    ['User Agent', runtime.userAgent ?? '未取得'],
    ['Angular 專案', project.root],
    ['專案版本', revision],
    ...(project.packages?.length ? [['相依套件版本', project.packages.map(item => `${item.name} ${item.version}`).join(', ')]] : []),
    ...(model.environment ?? []),
    ['tsconfig', sources.tsconfig],
    ['測試套件', `${sources.suite.root}, 進入點 ${sources.suite.entry}`],
    ...sources.suite.files.map(file => ['套件檔案', `${file.name} ${file.sha256.slice(0, 12)}`]),
    ...(model.renderer ? [['HTML 產生器', `report-html ${model.renderer.version}`]] : []),
  ];
}

export const verdictText = result => {
  if (result.status === 'error') return result.message ?? '';
  const shown = result.status === 'failed' ? result.assertions.filter(item => !item.pass) : result.assertions;
  return shown.map(item => `${item.pass ? '✓' : '✗'} ${item.label}: 實際 ${JSON.stringify(item.actual)}${Object.hasOwn(item, 'expected') ? `, 預期 ${JSON.stringify(item.expected)}` : ''}`).join('\n');
};

const cell = value => {
  const text = typeof value === 'string' ? value : JSON.stringify(value);
  return String(text ?? '').replace(/\|/g, '\\|').replace(/\r?\n/g, '<br>');
};

export function renderMarkdown(model) {
  const { summary } = model;
  const lines = [
    `# ${model.title ?? '元件測試報告'}`, '',
    '## 版本資訊', '',
    '| 項目 | 內容 |', '| --- | --- |',
    ...versionRows(model).map(([key, value]) => `| ${key} | ${cell(value)} |`),
    '',
  ];
  if (model.error) lines.push('## 設定或編譯錯誤', '', '```text', model.error, '```', '');
  lines.push('## 結果摘要', '', '| 通過 | 不通過 | 錯誤 | 觀察 | 合計 |', '| --- | --- | --- | --- | --- |',
    `| ${summary.passed} | ${summary.failed} | ${summary.error} | ${summary.info} | ${summary.total} |`, '');
  if (model.results.length) {
    lines.push('## 案例', '', '| 編號 | 群組 | 案例 | 狀態 | 判定 | 觀察值 |', '| --- | --- | --- | --- | --- | --- |');
    for (const result of model.results)
      lines.push(`| ${cell(result.id)} | ${cell(result.group)} | ${cell(result.name)} | ${STATUS_LABELS[result.status]} | ${cell(verdictText(result))} | ${cell(result.observed ?? '')} |`);
    lines.push('');
  }
  if (model.consoleErrors.length) lines.push('## 瀏覽器錯誤訊息', '', ...model.consoleErrors.map(text => `- ${cell(text)}`), '');
  lines.push('## 證據範圍', '', ...model.limits.map(text => `- ${text}`), '');
  return lines.join('\n');
}
