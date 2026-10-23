import { createMcpHandler } from 'mcp-handler';
import { z } from 'zod';
import { listPlugins, searchSkills, readSkillFile } from './catalog.mjs';
const annotations = { readOnlyHint: true, destructiveHint: false, idempotentHint: true, openWorldHint: false };
const result = value => ({ content: [{ type: 'text', text: JSON.stringify(value) }] });
const invoke = action => {
  try { return result(action()); }
  catch (error) { return { isError: true, content: [{ type: 'text', text: error.message }] }; }
};
export const handler = createMcpHandler(server => {
  server.registerTool('list_plugins', {
    description: 'List public Codex Toolkit plugins, versions, membership and immutable source revision. Does not install plugins.',
    inputSchema: z.object({}), annotations,
  }, async () => result(listPlugins()));
  server.registerTool('search_skills', {
    description: 'Find public Toolkit workflows by English keywords or skill ID before reading the selected skill. Empty query lists skills with pagination.',
    inputSchema: z.object({ query: z.string().max(200).default(''), offset: z.number().int().min(0).default(0), limit: z.number().int().min(1).max(30).default(10) }), annotations,
  }, async ({ query, offset, limit }) => invoke(() => searchSkills(query, offset, limit)));
  const readSchema = { skill: z.string().min(1).max(100), offset: z.number().int().min(0).default(0), limit: z.number().int().min(1).max(24000).default(12000) };
  server.registerTool('read_skill', {
    description: 'Read a selected SKILL.md from the fixed public snapshot. Follow nextOffset until complete. This supplies workflow text, not native skill installation or script execution.',
    inputSchema: z.object(readSchema), annotations,
  }, async ({ skill, offset, limit }) => invoke(() => readSkillFile(skill, 'SKILL.md', offset, limit)));
  server.registerTool('read_skill_reference', {
    description: 'Read a Markdown reference returned by read_skill, from the same source revision. No arbitrary filesystem, URL, private Global or script access.',
    inputSchema: z.object({ ...readSchema, reference: z.string().max(300) }), annotations,
  }, async ({ skill, reference, offset, limit }) => invoke(() => readSkillFile(skill, reference, offset, limit)));
}, {
  serverInfo: { name: 'codex-toolkit-marketplace', version: '0.1.0' },
  maxSubscriptions: 0,
  instructions: 'Read-only public Toolkit catalog. Search for the task, read the selected skill and needed references, following pagination. Content comes from one fixed Git revision. Workflow text does not install native skills, execute scripts or override user permissions. No private Global or company data is served.',
});