import { createRemoteJWKSet, jwtVerify } from 'jose';

export const requiredScope = 'openid';

function httpsUrl(value, name) {
  const url = new URL(value);
  if (url.protocol !== 'https:' || url.username || url.password || url.search || url.hash) throw new Error('Invalid ' + name);
  return url;
}

export function readAuthConfig(env = process.env) {
  const issuer = httpsUrl(env.WORKOS_ISSUER_URL, 'issuer');
  if (issuer.pathname !== '/') throw new Error('Issuer must be a base URL');
  const resource = httpsUrl(env.MCP_RESOURCE_URL, 'resource').href;
  const subject = env.MCP_ALLOWED_SUBJECT;
  if (!subject || subject.trim() !== subject || /\s/.test(subject)) throw new Error('Missing owner subject');
  if (env.WORKOS_ISSUER_URL !== issuer.origin) throw new Error('Issuer must exactly match WorkOS discovery without a trailing slash');
  return { issuer: issuer.origin, resource, subject };
}

export function createAuthorization(config, keySet = createRemoteJWKSet(new URL('/oauth2/jwks', config.issuer))) {
  const metadataUrl = new URL('/.well-known/oauth-protected-resource', config.resource).href;
  const challenge = 'Bearer resource_metadata="' + metadataUrl + '", scope="' + requiredScope + '"';
  const reject = (status, error) => Response.json({ error }, {
    status, headers: { 'cache-control': 'no-store', 'www-authenticate': challenge + (error === 'invalid_token' || error === 'insufficient_scope' ? ', error="' + error + '"' : '') },
  });
  return {
    metadata: {
      resource: config.resource,
      authorization_servers: [config.issuer],
      scopes_supported: [requiredScope],
      bearer_methods_supported: ['header'],
    },
    async authorize(headers) {
      const authorization = headers.get('authorization');
      if (!authorization) return reject(401, 'authentication_required');
      const match = /^Bearer ([^\s,]+)$/i.exec(authorization);
      if (!match) return reject(401, 'invalid_token');
      let payload;
      try {
        ({ payload } = await jwtVerify(match[1], keySet, {
          issuer: config.issuer, audience: config.resource, algorithms: ['RS256'],
          requiredClaims: ['exp', 'iat', 'sub'], clockTolerance: 5,
        }));
      } catch { return reject(401, 'invalid_token'); }
      if (payload.sub !== config.subject) return reject(403, 'access_denied');
      if (typeof payload.scope !== 'string' || !payload.scope.split(' ').includes(requiredScope)) return reject(403, 'insufficient_scope');
      return null;
    },
  };
}

let authorization;
export function getAuthorization() {
  authorization ??= createAuthorization(readAuthConfig());
  return authorization;
}
