const voidTags = new Set([
  'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input',
  'link', 'meta', 'param', 'source', 'track', 'wbr',
]);

module.exports = function protectedCopy(context, options = {}) {
  const { Syntax, getSource } = context;
  const texts = options.texts ?? [];
  if (!Array.isArray(texts) || texts.some(text => typeof text !== 'string' || !text.length))
    throw new TypeError('protected-copy texts must be nonempty literal strings');
  const stack = [];
  const literalRanges = [];
  return {
    [Syntax.Document]() {
      const source = getSource();
      for (const text of texts) {
        let index = source.indexOf(text);
        while (index !== -1) {
          const range = [index, index + text.length];
          literalRanges.push(range);
          context.shouldIgnore(range);
          index = source.indexOf(text, index + text.length);
        }
      }
    },
    [Syntax.Str](node) {
      // A contextual rule can start before a protected phrase and replace it.
      // Protect the containing text node so that its fix cannot cross the label.
      if (literalRanges.some(([start, end]) => start < node.range[1] && node.range[0] < end))
        context.shouldIgnore(node.range);
    },
    [Syntax.Html](node) {
      context.shouldIgnore(node.range);
      const source = getSource(node);
      if (/^\s*<!--/u.test(source)) return;
      // HTML tags are sibling AST nodes around inline UI text, not its parents.
      const tags = source.matchAll(/<\/?([a-z][a-z0-9:-]*)\b(?:[^"'<>]|"[^"]*"|'[^']*')*>/giu);
      for (const tag of tags) {
        const name = tag[1].toLowerCase();
        if (tag[0].startsWith('</')) {
          const index = stack.findLastIndex(open => open.name === name);
          if (index !== -1) {
            context.shouldIgnore([stack[index].start, node.range[0] + tag.index + tag[0].length]);
            stack.length = index;
          }
        } else if (!voidTags.has(name) && !/\/\s*>$/u.test(tag[0])) {
          stack.push({ name, start: node.range[0] + tag.index });
        }
      }
    },
    [`${Syntax.Document}:exit`](node) {
      // Preserve uncertain markup instead of fixing through an unclosed tag.
      if (stack.length) context.shouldIgnore([stack[0].start, node.range[1]]);
    },
  };
};
