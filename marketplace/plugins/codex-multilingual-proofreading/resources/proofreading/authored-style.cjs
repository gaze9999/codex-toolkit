const patterns = [
  ['preface', /\b(?:it is|it['’]s) (?:important to note|worth noting)(?: that)?\b/giu],
  ['liability', /\b(?:for (?:informational|educational) purposes only|no (?:warranties|guarantees) (?:are )?(?:given|provided))\b/giu],
  ['concision', /\b(?:in order to|at this point in time|due to the fact that)\b/giu],
  ['liability', /僅供(?:參考|說明|示意)(?:之用)?/gu],
  ['liability', /(?:不構成任何|不提供任何|無法提供任何)(?:保證|擔保|建議)/gu],
  ['preface', /(?:值得注意的是|需要特別說明的是|必須強調的是)/gu],
];

const messages = {
  en: {
    preface: 'State the result or action directly; review this filler preface',
    liability: 'Review this boilerplate; retain required source text or state the concrete operating condition',
    concision: 'Use a shorter equivalent while preserving facts, quantities and conditions',
  },
  'zh-TW': {
    preface: '直接說明結果或動作, 刪除無作用的前言, 需人工判讀',
    liability: '檢查制式免責敘述, 保留必要原文或改述具體操作條件, 需人工判讀',
    concision: '採用精簡英文, 保留事實、數量與必要條件, 需人工判讀',
  },
};

function rule(context, options = {}) {
  const { Syntax, RuleError, report, getSource } = context;
  const language = options.language ?? 'en';
  if (!Object.hasOwn(messages, language)) throw new Error('Choose en or zh-TW for authored-style messages');
  let excluded = 0;
  return {
    [Syntax.BlockQuote]() { excluded++; },
    [`${Syntax.BlockQuote}:exit`]() { excluded--; },
    [Syntax.Link]() { excluded++; },
    [`${Syntax.Link}:exit`]() { excluded--; },
    [Syntax.Str](node) {
      if (excluded) return;
      const text = getSource(node);
      if (/[\u3040-\u30ff]/u.test(text)) return;
      const ranges = [...text.matchAll(/https?:\/\/\S+|「[^」]*」|『[^』]*』|“[^”]*”|"[^"\n]*"/gu)]
        .map(match => [match.index, match.index + match[0].length]);
      for (const [kind, pattern] of patterns) {
        for (const match of text.matchAll(pattern)) {
          if (!ranges.some(([start, end]) => start <= match.index && match.index < end)) {
            report(node, new RuleError(messages[language][kind], { index: match.index }));
          }
        }
      }
    },
  };
}

module.exports = { linter: rule, fixer: rule };
