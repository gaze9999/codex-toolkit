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
