import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
const url = new URL(process.argv[2]);
if (url.protocol !== 'https:' && !(url.protocol === 'http:' && url.hostname === '127.0.0.1')) throw new Error('Use HTTPS or loopback');
const expected = JSON.parse(readFileSync(process.argv[3] ?? new URL('../data/catalog.json', import.meta.url), 'utf8'));

if (!process.env.MCP_ACCESS_TOKEN) throw new Error('Set MCP_ACCESS_TOKEN through an approved secret provider');
const options = { redirect: 'error', signal: AbortSignal.timeout(30000) };
const unauthenticated = await fetch(url, { ...options, method: 'POST', headers: { 'content-type': 'application/json' }, body: '{}' });
assert.equal(unauthenticated.status, 401, 'Unauthenticated MCP access must be denied');
assert.ok(unauthenticated.headers.get('www-authenticate')?.includes('resource_metadata='));
const metadataResponse = await fetch(new URL('/.well-known/oauth-protected-resource', url), { ...options, signal: AbortSignal.timeout(30000) });
assert.equal(metadataResponse.status, 200);
const metadata = await metadataResponse.json();
assert.ok(metadata.authorization_servers.length === 1 && metadata.authorization_servers[0].startsWith('https://'));
assert.deepEqual(metadata.scopes_supported, ['openid']);
for (const path of ['/data/catalog.json', '/auth.mjs', '/package.json']) {
  const response = await fetch(new URL(path, url), { ...options, signal: AbortSignal.timeout(30000) });
  assert.equal(response.status, 404, 'Deployment must not expose source or snapshot files');
}

let id = 0;
async function rpc(method, params) {
  const headers = { 'content-type': 'application/json', accept: 'application/json, text/event-stream' };
  if (process.env.MCP_ACCESS_TOKEN) headers.authorization = 'Bearer ' + process.env.MCP_ACCESS_TOKEN;
  const response = await fetch(url, { method: 'POST', redirect: 'error', signal: AbortSignal.timeout(30000), headers,
    body: JSON.stringify({ jsonrpc: '2.0', id: ++id, method, params }) });
  assert.equal(response.status, 200, 'Unexpected HTTP status');
  const text = await response.text();
  const data = text.split('\n').find(line => line.startsWith('data:'));
  const message = JSON.parse(data ? data.slice(5) : text);
  assert.ok(!message.error, 'MCP returned an error');
  return message.result;
}
const init = await rpc('initialize', { protocolVersion: '2025-03-26', capabilities: {}, clientInfo: { name: 'toolkit-verification', version: '0.1.0' } });
assert.equal(init.serverInfo.name, 'codex-toolkit-marketplace');
const tools = await rpc('tools/list', {});
assert.deepEqual(tools.tools.map(tool => tool.name).sort(), ['list_plugins','read_skill','read_skill_reference','search_skills']);
assert.ok(tools.tools.every(tool => tool.annotations.readOnlyHint === true));
const call = async (name, args) => {
  const result = await rpc('tools/call', { name, arguments: args });
  assert.ok(!result.isError, 'Tool returned an error');
  const value = JSON.parse(result.content[0].text);
  assert.equal(value.revision, expected.revision, 'Deployed revision differs from expected snapshot');
  assert.equal(value.repository, expected.repository);
  return value;
};
const plugins = await call('list_plugins', {});
assert.deepEqual(plugins.plugins, expected.plugins);
const search = await call('search_skills', { query: 'agent-governance' });
assert.ok(search.skills.some(skill => skill.id === 'agent-governance'));
const checked = [];
for (const reference of ['SKILL.md', 'references/component-authoring.md']) {
  const path = 'skills/agent-governance/' + reference;
  const source = expected.files[path];
  assert.ok(source, 'Expected source missing');
  let offset = 0;
  let text = '';
  do {
    const part = await call(reference === 'SKILL.md' ? 'read_skill' : 'read_skill_reference',
      { skill: 'agent-governance', ...(reference === 'SKILL.md' ? {} : { reference }), offset, limit: 6000 });
    assert.equal(part.path, path);
    assert.equal(part.sha256, source.sha256);
    assert.ok(part.text.length <= 6000);
    text += part.text;
    assert.ok(text.length <= source.text.length, 'Unexpected content length');
    if (part.nextOffset === null) break;
    assert.equal(part.nextOffset, offset + part.text.length, 'Invalid pagination');
    assert.ok(part.nextOffset > offset, 'Pagination did not advance');
    offset = part.nextOffset;
  } while (true);
  assert.equal(text, source.text);
  assert.equal(createHash('sha256').update(text, 'utf8').digest('hex'), source.sha256);
  checked.push({ path, sha256: source.sha256 });
}
const refused = await rpc('tools/call', { name: 'read_skill_reference', arguments: { skill: 'agent-governance', reference: '../AGENTS.md' } });
assert.equal(refused.isError, true);
console.log(JSON.stringify({ url: url.href, server: init.serverInfo, tools: tools.tools.length, plugins: plugins.plugins.length, revision: plugins.revision, checked, traversalRejected: true }));
