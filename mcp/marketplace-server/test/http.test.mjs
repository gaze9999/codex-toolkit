import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createServer } from 'node:http';
import { createEndpoint } from '../api/mcp.mjs';
import { authFixture } from './auth-fixture.mjs';

test('HTTP adapter serves MCP and rejects hostile origins and large requests', async () => {
  const { authorization, token } = await authFixture();
  const server = createServer(createEndpoint(() => authorization));
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  const url = 'http://127.0.0.1:' + server.address().port + '/mcp';
  try {
    const headers = { authorization: 'Bearer ' + await token(), 'content-type': 'application/json', accept: 'application/json, text/event-stream' };
    const response = await fetch(url, { method: 'POST', headers, body: JSON.stringify({ jsonrpc: '2.0', id: 1, method: 'tools/list', params: {} }) });
    assert.equal(response.status, 200);
    assert.ok((await response.text()).includes('read_skill'));
    const unauthorized = await fetch(url, { method: 'POST', body: '{}' });
    assert.equal(unauthorized.status, 401);
    const blocked = await fetch(url, { method: 'POST', headers: { ...headers, origin: 'https://untrusted.invalid' }, body: '{}' });
    assert.equal(blocked.status, 403);
    const large = await fetch(url, { method: 'POST', headers, body: 'x'.repeat(65537) });
    assert.equal(large.status, 413);
    const invalid = await fetch(url, { method: 'POST', headers, body: '{' });
    assert.equal(invalid.status, 400);
  } finally {
    server.closeAllConnections();
    await new Promise(resolve => server.close(resolve));
  }
});

test('HTTP authorization fails closed and discovery exposes no owner identifier', async () => {
  const { createMetadataEndpoint } = await import('../api/oauth.mjs');
  const { authorization } = await authFixture();
  const server = createServer((req, res) => {
    if (req.url === '/metadata') return createMetadataEndpoint(() => authorization)(req, res);
    return createEndpoint(() => { throw new Error('Missing configuration'); })(req, res);
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  const base = 'http://127.0.0.1:' + server.address().port;
  try {
    assert.equal((await fetch(base + '/mcp')).status, 503);
    const discovery = await fetch(base + '/metadata');
    assert.equal(discovery.status, 200);
    const data = await discovery.json();
    assert.equal(data.resource, 'https://mcp.example/mcp');
    assert.deepEqual(data.authorization_servers, ['https://tenant.example']);
    assert.ok(!JSON.stringify(data).includes('user_owner'));
    assert.equal((await fetch(base + '/metadata', { method: 'POST' })).status, 405);
  } finally {
    server.closeAllConnections();
    await new Promise(resolve => server.close(resolve));
  }
});

test('concurrent authenticated calls keep correlation isolated and omit payloads from diagnostics', async () => {
  const { authorization, token } = await authFixture();
  const logs = [];
  const server = createServer(createEndpoint(() => authorization, undefined, entry => logs.push(entry)));
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  try {
    const headers = { authorization: 'Bearer ' + await token(), 'content-type': 'application/json', accept: 'application/json, text/event-stream' };
    const cases = [
      ['search_skills', { query: 'agent-governance' }],
      ['read_skill', { skill: 'agent-governance', offset: 0, limit: 12000 }],
      ['read_skill_reference', { skill: 'agent-governance', reference: '../AGENTS.md' }],
    ];
    const replies = await Promise.all(Array.from({ length: 21 }, async (_, index) => {
      const [name, args] = cases[index % cases.length];
      const response = await fetch('http://127.0.0.1:' + server.address().port, {
        method: 'POST', headers, body: JSON.stringify({ jsonrpc: '2.0', id: index, method: 'tools/call', params: { name, arguments: args, _meta: { private: 'DO_NOT_LOG' } } }),
      });
      assert.equal(response.status, 200);
      const text = await response.text();
      assert.ok(text.includes(index % 3 === 2 ? 'Invalid reference' : 'revision'));
      return response.headers.get('x-mcp-request-id');
    }));
    assert.equal(new Set(replies).size, 21);
    for (const id of replies) {
      const entries = logs.filter(entry => entry.requestId === id);
      assert.equal(entries.length, 2);
      assert.equal(entries[1].phase, 'response');
      assert.equal(entries[1].status, 200);
    }
    assert.equal(logs.filter(entry => entry.toolError).length, 7);
    const output = JSON.stringify(logs);
    for (const secret of ['DO_NOT_LOG', headers.authorization, 'agent-governance', '../AGENTS.md', '798f55']) assert.ok(!output.includes(secret));
  } finally {
    server.closeAllConnections();
    await new Promise(resolve => server.close(resolve));
  }
});

test('authorization and response failures return bounded errors with phase evidence', async () => {
  for (const phase of ['authorization', 'handler', 'response']) {
    const logs = [];
    const authorize = async () => { if (phase === 'authorization') throw new Error('PRIVATE_TOKEN'); return null; };
    const processRequest = async () => {
      if (phase === 'handler') throw new Error('PRIVATE_ARGUMENT');
      return new Response(new ReadableStream({ start(controller) { controller.error(new Error('PRIVATE_CONTENT')); } }));
    };
    const server = createServer(createEndpoint(() => ({ authorize }), processRequest, entry => logs.push(entry)));
    await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
    try {
      const response = await fetch('http://127.0.0.1:' + server.address().port, { method: 'POST', body: '{}' });
      assert.equal(response.status, phase === 'authorization' ? 503 : 500);
      assert.ok(!(await response.text()).includes('PRIVATE_'));
      assert.equal(logs.at(-1).phase, phase);
      assert.ok(!JSON.stringify(logs).includes('PRIVATE_'));
    } finally {
      server.closeAllConnections();
      await new Promise(resolve => server.close(resolve));
    }
  }
});
test('preparsed body serialization and diagnostic sink failures remain bounded', async () => {
  const circular = {}; circular.self = circular;
  const server = createServer((req, res) => {
    req.body = circular;
    return createEndpoint(() => ({ authorize: async () => null }), undefined, () => { throw new Error('sink failed'); })(req, res);
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  try {
    const response = await fetch('http://127.0.0.1:' + server.address().port, { method: 'POST', body: '{}' });
    assert.equal(response.status, 400);
    assert.deepEqual(await response.json(), { error: 'Invalid request body' });
  } finally {
    server.closeAllConnections();
    await new Promise(resolve => server.close(resolve));
  }
});