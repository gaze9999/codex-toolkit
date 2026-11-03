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

test('limited rollout wording is profile advice without an automatic synonym', () => {
  const reports = check('先做試點, 再擴大試點');
  assert.equal(reports.length, 2);
  for (const report of reports) {
    assert.match(report.message, /profile.*先行驗證、試行或試辦.*人工判讀/u);
    assert.equal(report.fix, undefined);
  }
  assert.equal(check('先行驗證、試行與試辦').length, 0);
});

test('limited rollout advice preserves literal sources and excluded containers', () => {
  for (const text of ['來源「試點」', '來源『試點』', '來源 "試點"', 'https://example.test/試點', '檔案 D:\\試點\\來源.md']) {
    assert.equal(check(text).length, 0, text);
  }
  for (const container of ['BlockQuote', 'Link']) assert.equal(check('試點', container).length, 0);
});

test('Chinese sentence periods are reported without guessing a clause boundary', () => {
  for (const text of ['完成. 後續說明', '完成.後續說明', '完成。後續說明']) {
    const reports = check(text);
    assert.equal(reports.length, 1, text);
    assert.match(reports[0].message, /不加句號/u);
    assert.equal(reports[0].fix, undefined);
  }
  for (const text of ['完成.', '完成。']) {
    const reports = check(text);
    assert.equal(reports.length, 1, text);
    assert.equal(reports[0].fix.replacement, '');
  }
});

test('Chinese punctuation spacing is checked for existing halfwidth marks', () => {
  for (const mark of [',', ':', '?', '!']) {
    assert.equal(check('完成' + mark + '請確認')[0].fix.replacement, mark + ' ');
    assert.equal(check('完成' + mark + ' 請確認').length, 0);
    for (const spaces of ['  ', '\t', '　']) {
      assert.equal(check('完成' + mark + spaces + '請確認')[0].fix.replacement, mark + ' ');
    }
  }
});

test('numeric syntax, versions, filenames, URLs and source literals remain intact', () => {
  for (const text of [
    '版本 v0.2.0, 數量 1,000, 比例 1:2, 時間 12:30, 檔案 README.md 與 設定.json',
    '保留 https://example.test/a?x=1,y=2 與 D:\\github\\工具.md',
    '來源「完成。請確認」與 "版本:原文。"',
    '保留英文縮寫 e.g. 與 i.e. 的原有語法',
  ]) assert.equal(check(text).length, 0, text);
});
