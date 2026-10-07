const punctuation = new Map([
  ['，', ','], ['。', '.'], ['：', ':'],
  ['？', '?'], ['！', '!'], ['（', '('], ['）', ')'],
  ['［', '['], ['］', ']'],
]);

function rule(context) {
  const { Syntax, RuleError, report, getSource, fixer } = context;
  let excluded = 0;
  return {
    [Syntax.BlockQuote]() { excluded++; },
    [`${Syntax.BlockQuote}:exit`]() { excluded--; },
    [Syntax.Link]() { excluded++; },
    [`${Syntax.Link}:exit`]() { excluded--; },
    [Syntax.Str](node) {
      if (excluded) return;
      const text = getSource(node);
      // Apply the selected Chinese profile to prose, preserve Japanese and literal URLs
      if (!/[\u3400-\u9fff]/u.test(text) || /[\u3040-\u30ff]/u.test(text)) return;
      const protectedRanges = [...text.matchAll(/https?:\/\/\S+|「[^」]*」|『[^』]*』|“[^”]*”|"[^"\n]*"/gu)]
        .map(match => [match.index, match.index + match[0].length]);
      const protectedAt = index => protectedRanges.some(([start, end]) => start <= index && index < end);
      // Ambiguous governance wording needs a contextual choice, never an automatic fix.
      const governance = /(?:AGENTS(?:\.md)?|Agent|Codex|Skills?|Plugins?|MCP|個人|工作|任務|對話|工具|設定|權限)[ \t]*治理/giu;
      for (const match of text.matchAll(governance)) {
        if (!protectedAt(match.index)) report(node, new RuleError(
          '依用途使用工作規範、設定管理或權限管理, 正式治理名稱保留, 需人工判讀',
          { index: match.index },
        ));
      }
      // A text node can end before inline code, links or emphasis on the same line
      const remainingLine = getSource().slice(node.range[1]).split(/\r?\n/u, 1)[0];
      const atLineEnd = /^[\s*_~]*$/u.test(remainingLine);
      for (let index = 0; index < text.length; index++) {
        const mark = text[index];
        if (protectedAt(index)) continue;
        if (mark === ';' || mark === '；') {
          report(node, new RuleError('不要用分號分段, 依語意改為逗號或句號', { index }));
        } else if (punctuation.has(mark)) {
          let replacement = mark === '。' && !text.slice(index + 1).trim() && atLineEnd ? '' : punctuation.get(mark);
          if (/^[,.:?!]$/u.test(replacement) && text[index + 1] && !/\s|[)\]」』”]/u.test(text[index + 1])) replacement += ' ';
          report(node, new RuleError('繁中使用半形標點', {
            index, fix: fixer.replaceTextRange([index, index + 1], replacement),
          }));
        }
      }
      const end = /(?<!\.)\.(?!\.)\s*$/u.exec(text);
      if (end && atLineEnd && !protectedAt(end.index)) {
        report(node, new RuleError('繁中句尾不加句號, 保留檔名, 版本與小數中的句點', {
          index: end.index, fix: fixer.replaceTextRange([end.index, end.index + 1], ''),
        }));
      }
    },
  };
}

module.exports = { linter: rule, fixer: rule };
