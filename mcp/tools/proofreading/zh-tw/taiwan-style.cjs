const punctuation = new Map([
  ['，', ','], ['：', ':'],
  ['？', '?'], ['！', '!'], ['（', '('], ['）', ')'],
  ['［', '['], ['］', ']'],
]);
const spaced = new Set([',', ':', '?', '!']);

const agentTerms = [
  [/(?:AI|LLM)[ \t]*智能[體体]/giu, 'AI 代理程式 / AI 代理人'],
  [/多智能[體体]系統/gu, '多代理系統 (Multi-Agent System)'],
  [/單(?:一)?智能[體体]系統/gu, '單一代理系統 (Single-Agent System)'],
  [/子智能[體体]/gu, '子代理程式 (Subagent)'],
  [/智能[體体]編排/gu, '代理編排 (Agent Orchestration)'],
  [/智能[體体]框架/gu, '代理程式框架 (Agent Framework)'],
];

const han = /[\u3400-\u9fff]/u;
const kana = /[\u3040-\u30ff]/u;
const quoteOpenings = new Set(['「', '『', '“']);

function rule(context) {
  const { Syntax, RuleError, report, getSource, fixer } = context;
  let excluded = 0;
  const blocks = [];
  const enter = node => { blocks.push(getSource(node)); };
  const leave = () => { blocks.pop(); };
  return {
    [Syntax.BlockQuote]() { excluded++; },
    [`${Syntax.BlockQuote}:exit`]() { excluded--; },
    [Syntax.Link]() { excluded++; },
    [`${Syntax.Link}:exit`]() { excluded--; },
    // Punctuation separated from its sentence by inline code, emphasis or a link follows the block's language
    ...Object.fromEntries(['Paragraph', 'Header', 'TableCell'].filter(name => Syntax[name])
      .flatMap(name => [[Syntax[name], enter], [`${Syntax[name]}:exit`, leave]])),
    [Syntax.Str](node) {
      if (excluded) return;
      const text = getSource(node);
      // Apply the selected Chinese profile to prose, preserve Japanese and literal URLs
      if (kana.test(text)) return;
      // Text without Chinese characters is checked only for the punctuation that follows a Chinese inline element
      let limit = text.length;
      if (!han.test(text)) {
        const block = blocks.at(-1);
        limit = /^[\s\p{P}\p{S}]*/u.exec(text)[0].trimEnd().length;
        if (!limit || !block || !han.test(block) || kana.test(block)) return;
      }
      const literalRanges = [...text.matchAll(/https?:\/\/\S+|[A-Za-z]:[\\/][^\s<>"「」『』“”]+|\b(?:[A-Za-z]\.){2,}/gu)]
        .map(match => [match.index, match.index + match[0].length]);
      const quoteRanges = [...text.matchAll(/「[^」]*」|『[^』]*』|“[^”]*”|"[^"\n]*"/gu)]
        .map(match => [match.index, match.index + match[0].length]);
      const literalAt = index => literalRanges.some(([start, end]) => start <= index && index < end);
      const protectedAt = index => literalAt(index) || quoteRanges.some(([start, end]) => start <= index && index < end);
      // Quote marks are authored punctuation even when the quoted words are original.
      // Original passages that carry their own marks belong in a blockquote, code or the protected-copy list.
      for (const [start] of quoteRanges) {
        if (quoteOpenings.has(text[start]) && !literalAt(start)) report(node, new RuleError(
          '繁中自撰文字使用半形引號 "...", 原文自帶的引號改放引用區塊、程式碼或保留清單, 需人工判讀',
          { index: start },
        ));
      }
      // Ambiguous governance wording needs a contextual choice, never an automatic fix.
      const governance = /(?:AGENTS(?:\.md)?|Codex|Skills?|Plugins?|MCP|個人|工作|任務|對話|工具|設定|權限)[ \t]*治理/giu;
      for (const match of text.matchAll(governance)) {
        if (!protectedAt(match.index)) report(node, new RuleError(
          '工作指示、來源設定或存取權限依用途採工作規範、設定管理或權限管理, 政策、權責、身分與風險的治理語意保留, 需人工判讀',
          { index: match.index },
        ));
      }
      // Agent aliases are scoped project advice; preserve formal names and literal sources.
      for (const [pattern, preferred] of agentTerms) {
        for (const match of text.matchAll(pattern)) {
          if (!protectedAt(match.index)) report(node, new RuleError(
            `代理系統工程用語建議採 ${preferred}, 正式名稱與來源用語保留, 需人工判讀`,
            { index: match.index },
          ));
        }
      }
      for (const match of text.matchAll(/試點/gu)) {
        if (!protectedAt(match.index)) report(node, new RuleError(
          '此繁中 profile 偏好先行驗證、試行或試辦, 依語意選擇, 正式名稱與來源用語保留, 需人工判讀',
          { index: match.index },
        ));
      }
      // A text node can end before inline code, links or emphasis on the same line
      const remainingLine = getSource().slice(node.range[1]).split(/\r?\n/u, 1)[0];
      const atLineEnd = /^[\s*_~]*$/u.test(remainingLine);
      for (let index = 0; index < limit; index++) {
        const mark = text[index];
        if (protectedAt(index)) continue;
        const next = text[index + 1] ?? remainingLine[0];
        const follows = index + 1 < text.length || !atLineEnd;
        const numeric = [',', ':', '，', '：'].includes(mark)
          && /[0-9]/u.test(text[index - 1] ?? '') && /[0-9]/u.test(text[index + 1] ?? '');
        const sentenceDot = mark === '.' && text[index - 1] !== '.' && text[index + 1] !== '.'
          && (index + 1 === text.length || /[\s)\]」』”\u3400-\u9fff]/u.test(text[index + 1]));
        if (mark === ';' || mark === '；') {
          report(node, new RuleError('不要用分號分段, 依語意改為逗號或換行', { index }));
        } else if (mark === '。' || sentenceDot) {
          const terminal = !text.slice(index + 1).trim() && atLineEnd;
          report(node, new RuleError('繁中敘述不加句號, 依語意改為逗號或換行, 保留檔名、版本及其他語言語法', {
            index,
            ...(terminal ? { fix: fixer.replaceTextRange([index, index + 1], '') } : {}),
          }));
        } else if (punctuation.has(mark)) {
          let replacement = punctuation.get(mark);
          if (spaced.has(replacement) && !numeric && follows && next && !/\s|[)\]」』”]/u.test(next)) replacement += ' ';
          report(node, new RuleError('繁中使用半形標點', {
            index, fix: fixer.replaceTextRange([index, index + 1], replacement),
          }));
        } else if (spaced.has(mark) && !numeric && follows && next && !/[)\]」』”]/u.test(next)) {
          const spaces = /^[^\S\r\n]*/u.exec(text.slice(index + 1))[0];
          const after = text[index + 1 + spaces.length] ?? remainingLine[0];
          const contentFollows = index + 1 + spaces.length < text.length || !atLineEnd;
          if (contentFollows && after && !/[\r\n]/u.test(after) && spaces !== ' ') {
            report(node, new RuleError('半形逗號、冒號、問號及驚嘆號後有文字時加一個半形空格', {
              index, fix: fixer.replaceTextRange([index, index + 1 + spaces.length], mark + ' '),
            }));
          }
        }
      }
    },
  };
}

module.exports = { linter: rule, fixer: rule };
