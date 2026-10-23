import { test } from 'node:test';
import assert from 'node:assert/strict';
import { listPlugins, searchSkills, readSkillFile } from '../catalog.mjs';
import { handler } from '../handler.mjs';

test('catalog contains public plugins and paginated skills', () => {
  assert.ok(listPlugins().plugins.length > 0);
  assert.equal(searchSkills('', 0, 1).skills.length, 1);
  assert.equal(searchSkills('', 0, 1).nextOffset, 1);
  assert.ok(searchSkills('agent-governance').skills.some(item => item.id === 'agent-governance'));
});
test('source reads have fixed provenance and complete pagination', () => {
  const whole = readSkillFile('agent-governance');
  assert.match(whole.revision, /^[a-f0-9]{40}$/);
  assert.match(whole.sha256, /^[a-f0-9]{64}$/);
  const part = readSkillFile('agent-governance', 'SKILL.md', 0, 10);
  assert.equal(part.text + readSkillFile('agent-governance', 'SKILL.md', 10).text, whole.text);
  for (const reference of whole.references) assert.ok(readSkillFile('agent-governance', reference).text);
});
test('private, traversal, URL and unlisted paths are rejected', () => {
  for (const path of ['../AGENTS.md', '/etc/passwd', 'references/../../secret.md', 'https://example.com/a.md', 'references/nope.md', 'references\\secret.md']) {
    assert.throws(() => readSkillFile('agent-governance', path));
  }
  assert.throws(() => readSkillFile('private-global'));
  assert.throws(() => readSkillFile('agent-governance', 'SKILL.md', -1));
  assert.throws(() => searchSkills('', 0, 100));
});
async function rpc(method, params) {
  const response = await handler(new Request('http://localhost/mcp', {
    method: 'POST', headers: { 'content-type': 'application/json', accept: 'application/json, text/event-stream' },
    body: JSON.stringify({ jsonrpc: '2.0', id: 1, method, params }),
  }));
  const text = await response.text();
  assert.equal(response.status, 200, text);
  return text.startsWith('event:') || text.startsWith('data:') ? JSON.parse(text.split('\n').find(line => line.startsWith('data:')).slice(5)) : JSON.parse(text);
}
test('actual MCP initialization, discovery and tool calls', async () => {
  const init = await rpc('initialize', { protocolVersion: '2025-03-26', capabilities: {}, clientInfo: { name: 'toolkit-test', version: '1' } });
  assert.ok(init.result.serverInfo);
  const tools = await rpc('tools/list', {});
  assert.equal(tools.result.tools.length, 4);
  for (const tool of tools.result.tools) assert.equal(tool.annotations.readOnlyHint, true);
  const read = await rpc('tools/call', { name: 'read_skill', arguments: { skill: 'agent-governance' } });
  assert.ok(JSON.parse(read.result.content[0].text).text.includes('name:'));
  const invalid = await rpc('tools/call', { name: 'read_skill_reference', arguments: { skill: 'agent-governance', reference: '../AGENTS.md' } });
  assert.equal(invalid.result.isError, true);
});
