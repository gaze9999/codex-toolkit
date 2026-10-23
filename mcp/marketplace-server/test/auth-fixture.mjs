import { generateKeyPair, exportJWK, createLocalJWKSet, SignJWT } from 'jose';
import { createAuthorization } from '../auth.mjs';

export async function authFixture() {
  const { publicKey, privateKey } = await generateKeyPair('RS256');
  const key = { ...await exportJWK(publicKey), kid: 'fixture', alg: 'RS256' };
  const config = { issuer: 'https://tenant.example', resource: 'https://mcp.example/mcp', subject: 'user_owner' };
  const authorization = createAuthorization(config, createLocalJWKSet({ keys: [key] }));
  async function token(overrides = {}, signingKey = privateKey) {
    const now = Math.floor(Date.now() / 1000);
    return new SignJWT({ iss: config.issuer, aud: config.resource, sub: config.subject, scope: 'openid', iat: now, exp: now + 60, ...overrides })
      .setProtectedHeader({ alg: 'RS256', kid: 'fixture' }).sign(signingKey);
  }
  return { config, authorization, token };
}
