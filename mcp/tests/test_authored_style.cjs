const { test } = require('node:test');
const assert = require('node:assert/strict');
const path = require('node:path');
const rule = require(path.join(__dirname, '../tools/proofreading/authored-style.cjs'));

function check(text, { language = 'en', container } = {}) {
  const reports = [];
  class RuleError extends Error {
    constructor(message, options) { super(message); Object.assign(this, options); }
  }
  const visitors = rule.linter({
    Syntax: { Str: 'Str', BlockQuote: 'BlockQuote', Link: 'Link' },
    RuleError,
    getSource: node => node ? node.value : text,
    report: (node, error) => reports.push(error),
  }, { language });
  if (container) visitors[container]();
  visitors.Str({ value: text, range: [0, text.length] });
  return reports;
}

test('English prefaces and wordy phrases receive precise advice', () => {
  for (const text of ['It is worth noting that the file was saved.', "It's important to note that access is required.", 'In order to save the file, select a folder.', 'At this point in time, the task is paused.', 'Retry due to the fact that the request timed out.']) {
    const result = check(text);
    assert.equal(result.length, 1, text);
    assert.equal(result[0].index, text === 'Retry due to the fact that the request timed out.' ? 6 : 0);
    assert.equal(result[0].fix, undefined);
  }
});
test('English and Chinese liability patterns remain review-only', () => {
  for (const text of ['For informational purposes only', 'No guarantees are provided', '僅供參考', '不構成任何保證']) {
    const result = check(text);
    assert.equal(result.length, 1, text);
    assert.match(result[0].message, /Review/u);
    assert.equal(result[0].fix, undefined);
  }
});
test('Taiwan messages preserve the selected language', () => {
  const result = check('值得注意的是, 檔案已儲存', { language: 'zh-TW' });
  assert.equal(result.length, 1);
  assert.match(result[0].message, /直接說明結果或動作/u);
  assert.equal(result[0].fix, undefined);
});
test('direct results and concrete conditions are accepted', () => {
  for (const text of ['The file was saved.', 'Write access is required to update the file.', 'The operation retries twice after a timeout.', '授權後才能推送儲存庫', '來源已更新, 用戶端載入待驗收', 'For a guarantee that applies to this API, see its specification.']) {
    assert.equal(check(text).length, 0, text);
  }
});
test('quoted sources and URLs remain unchanged', () => {
  for (const text of ['The source says "For informational purposes only".', '原文「僅供參考」', '原文『不構成任何保證』', 'https://example.test/僅供參考']) assert.equal(check(text).length, 0, text);
});
test('blockquotes and link labels are excluded', () => {
  assert.equal(check('It is worth noting that the file was saved.', { container: 'BlockQuote' }).length, 0);
  assert.equal(check('僅供參考', { container: 'Link' }).length, 0);
});
test('Japanese and unrelated word senses remain unchanged', () => {
  assert.equal(check('僅供參考という引用です。').length, 0);
  assert.equal(check('Sort the records in order, then save them.').length, 0);
});
test('unsupported message locale fails explicitly', () => {
  assert.throws(() => check('Saved', { language: 'ja' }), /Choose en or zh-TW/u);
});
