const path = require('node:path');
const { createRequire } = require('node:module');

const entry = process.argv[2];
if (!entry || path.basename(entry) !== 'textlint.js') throw new Error('Use the selected textlint entrypoint');
const load = createRequire(path.join(path.dirname(entry), '..', 'package.json'));
const { McpServer } = load('@modelcontextprotocol/server');
const original = McpServer.prototype.registerTool;

// Keep upstream tools and schemas, normalize textlint 15.8 fix-result extra fields
McpServer.prototype.registerTool = function (name, config, handler) {
  return original.call(this, name, config, async (...args) => {
    const result = await handler(...args);
    if (result.isError || !result.structuredContent || !config.outputSchema) return result;
    const structuredContent = config.outputSchema.parse(result.structuredContent);
    return {
      ...result,
      structuredContent,
      content: result.content.map(item => item.type === 'text'
        ? { ...item, text: JSON.stringify(structuredContent, null, 2) }
        : item),
    };
  });
};

process.argv.splice(1, 1);
require(entry);
