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
  for (const text of ['AGENTS.md 治理', '個人治理', 'Plugin 治理', '權限治理']) {
    const result = check(text);
    assert.equal(result.length, 1, text);
    assert.match(result[0].message, /人工判讀/u);
    assert.equal(result[0].fix, undefined);
  }
});
test('established governance terms retain their meaning', () => {
  for (const text of ['AI 治理', 'AI 代理治理', 'AI Agent 治理', 'Agent 治理', '資料治理', '公司治理', '治理理論']) assert.equal(check(text).length, 0, text);
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
test('scoped agent aliases are advisory and do not auto-fix meaning', () => {
  for (const text of ['AI 智能體', 'LLM智能体', '多智能體系統', '單智能體系統', '子智能體', '智能體編排', '智能體框架']) {
    const reports = check(text);
    assert.equal(reports.length, 1, text);
    assert.match(reports[0].message, /工程用語.*人工判讀/u);
    assert.equal(reports[0].fix, undefined);
  }
});
test('accepted agent translations and architecture distinctions remain unmodified', () => {
  for (const text of ['AI 代理程式、AI 代理人、AI 代理', '代理編排與代理執行控制框架', '上下文工程、代理可觀測性與代理評估', '事件記錄與記錄檔', 'MCP、A2A、A2UI、AG-UI']) {
    assert.equal(check(text).length, 0, text);
  }
});
test('agent alias advice preserves quoted and non-agent senses', () => {
  for (const text of ['原文「AI 智能體」', '原文『多智能體系統』', '智能體研究與保險代理人', 'https://example.test/AI智能體']) {
    assert.equal(check(text).length, 0, text);
  }
  assert.equal(check('AI 智能體', 'BlockQuote').length, 0);
  assert.equal(check('AI 智能體', 'Link').length, 0);
});
test('existing punctuation behavior is preserved', () => {
  assert.equal(check('完成，請確認')[0].fix.replacement, ', ');
  assert.equal(check('完成; 請確認')[0].fix, undefined);
  assert.equal(check('中文並列、台灣用語').length, 0);
});
