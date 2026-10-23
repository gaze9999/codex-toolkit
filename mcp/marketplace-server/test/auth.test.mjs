import { test } from 'node:test';
import assert from 'node:assert/strict';
import { generateKeyPair } from 'jose';
import { authFixture } from './auth-fixture.mjs';
import { readAuthConfig } from '../auth.mjs';

test('WorkOS validates signature, issuer, audience, expiry, owner and scope', async () => {
  const { authorization, token } = await authFixture();
  const authorize = value => authorization.authorize(new Headers(value ? { authorization: 'Bearer ' + value } : {}));
  assert.equal(await authorize(await token()), null);
  const missing = await authorize();
  assert.equal(missing.status, 401);
  assert.match(missing.headers.get('www-authenticate'), /resource_metadata="https:\/\/mcp.example\/\.well-known\/oauth-protected-resource"/);
  for (const claims of [{ iss: 'https://attacker.example/' }, { aud: 'another-api' }, { exp: 1 }, { exp: undefined }, { sub: undefined }, { nbf: 9999999999 }]) {
    assert.equal((await authorize(await token(claims))).status, 401);
  }
  const other = await generateKeyPair('RS256');
  assert.equal((await authorize(await token({}, other.privateKey))).status, 401);
  assert.equal((await authorize('invalid')).status, 401);
  assert.equal((await authorize(await token({ sub: 'user_other' }))).status, 403);
  assert.equal((await authorize(await token({ scope: 'read:other' }))).status, 403);
  assert.equal((await authorization.authorize(new Headers({ authorization: 'Bearer a, Bearer b' }))).status, 401);
  assert.deepEqual(authorization.metadata.scopes_supported, ['openid']);
});

test('WorkOS configuration fails closed and accepts only explicit HTTPS settings', () => {
  assert.throws(() => readAuthConfig({}));
  const env = { WORKOS_ISSUER_URL: 'https://tenant.example', MCP_RESOURCE_URL: 'https://mcp.example/mcp', MCP_ALLOWED_SUBJECT: 'user_owner' };
  assert.equal(readAuthConfig(env).issuer, env.WORKOS_ISSUER_URL);
  for (const update of [{ WORKOS_ISSUER_URL: 'https://tenant.example/' }, { WORKOS_ISSUER_URL: 'http://tenant.example/' }, { MCP_RESOURCE_URL: 'https://user:password@mcp.example/mcp' }, { MCP_ALLOWED_SUBJECT: '' }, { WORKOS_ISSUER_URL: 'https://tenant.example/path' }]) {
    assert.throws(() => readAuthConfig({ ...env, ...update }));
  }
});
