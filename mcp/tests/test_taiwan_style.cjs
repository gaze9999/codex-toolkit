const { test } = require('node:test');
const assert = require('node:assert/strict');
const path = require('node:path');
const rule = require(path.join(__dirname, '../tools/proofreading/zh-tw/taiwan-style.cjs'));

function check(text, container) {
  const reports = [];
  class RuleError extends Error {
    constructor(message, options) { super(message); Object.assign(this, options); }
  }
  const context = {
    Syntax: { Str: 'Str', BlockQuote: 'BlockQuote', Link: 'Link' },
    RuleError,
    getSource: node => node ? node.value : text,
    report: (node, error) => reports.push(error),
    fixer: { replaceTextRange: (range, replacement) => ({ range, replacement }) },
  };
  const visitors = rule.linter(context);
  if (container) visitors[container]();
  visitors.Str({ value: text, range: [0, text.length] });
  return reports;
}

test('agent and tooling wording receives contextual advice without a fix', () => {
  for (const text of ['Agent 治理', 'AGENTS.md 治理', '個人治理', 'Plugin 治理', '權限治理']) {
    const result = check(text);
    assert.equal(result.length, 1, text);
    assert.match(result[0].message, /人工判讀/u);
    assert.equal(result[0].fix, undefined);
  }
});
test('established governance terms retain their meaning', () => {
  for (const text of ['AI 治理', '資料治理', '公司治理', '治理理論']) assert.equal(check(text).length, 0, text);
});
test('concrete work settings and permissions wording is accepted', () => {
  assert.equal(check('工作規範、設定管理、權限管理').length, 0);
});
test('quoted formal names and identifiers remain literal', () => {
  assert.equal(check('正式名稱「Agent 治理」').length, 0);
  assert.equal(check('保留 agent-governance 與 governancePolicy').length, 0);
});
test('blockquote and link labels remain excluded', () => {
  assert.equal(check('Agent 治理', 'BlockQuote').length, 0);
  assert.equal(check('Agent 治理', 'Link').length, 0);
});
test('English and Japanese retain their own conventions', () => {
  assert.equal(check('Agent governance.').length, 0);
  assert.equal(check('Agent 治理について。').length, 0);
});
test('existing punctuation behavior is preserved', () => {
  assert.equal(check('完成，請確認')[0].fix.replacement, ', ');
  assert.equal(check('完成; 請確認')[0].fix, undefined);
  assert.equal(check('中文並列、台灣用語').length, 0);
});
