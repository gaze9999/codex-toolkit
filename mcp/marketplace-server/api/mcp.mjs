import { handler } from '../handler.mjs';
import { getAuthorization } from '../auth.mjs';
export function createEndpoint(resolveAuthorization = getAuthorization) { return async function endpoint(req, res) {
  if (!['POST', 'GET', 'DELETE'].includes(req.method)) { res.writeHead(405); return res.end(); }
  const host = req.headers.host;
  if (!host || !/^[a-zA-Z0-9.:-]+$/.test(host)) { res.writeHead(400); return res.end(); }
  const origin = req.headers.origin;
  if (origin && origin !== 'https://' + host && origin !== 'http://' + host && origin !== 'https://chatgpt.com') {
    res.writeHead(403); return res.end();
  }
  let authorization;
  try { authorization = resolveAuthorization(); }
  catch {
    res.writeHead(503, { 'content-type': 'application/json', 'cache-control': 'no-store' });
    return res.end(JSON.stringify({ error: 'Authentication is not configured' }));
  }
  const authHeaders = new Headers();
  const bearer = req.headers.authorization;
  if (bearer !== undefined) authHeaders.set('authorization', Array.isArray(bearer) ? bearer.join(', ') : bearer);
  const denied = await authorization.authorize(authHeaders);
  if (denied) {
    res.writeHead(denied.status, Object.fromEntries(denied.headers));
    return res.end(await denied.text());
  }
  let body;
  if (req.method === 'POST') {
    if (req.body !== undefined) body = typeof req.body === 'string' ? req.body : JSON.stringify(req.body);
    else {
      const chunks = []; let size = 0;
      for await (const chunk of req) {
        size += chunk.length;
        if (size > 65536) { res.writeHead(413); return res.end(); }
        chunks.push(chunk);
      }
      body = Buffer.concat(chunks).toString('utf8');
    }
    if (Buffer.byteLength(body) > 65536) { res.writeHead(413); return res.end(); }
  }
  const headers = new Headers();
  for (const [key, value] of Object.entries(req.headers)) if (value !== undefined) headers.set(key, Array.isArray(value) ? value.join(', ') : value);
  try {
    const response = await handler(new Request('https://' + host + '/api/mcp', { method: req.method, headers, ...(body !== undefined ? { body } : {}) }));
    res.writeHead(response.status, Object.fromEntries(response.headers));
    res.end(Buffer.from(await response.arrayBuffer()));
  } catch {
    res.writeHead(500, { 'content-type': 'application/json' });
    res.end(JSON.stringify({ error: 'MCP request failed' }));
  }
}; }
export default createEndpoint();
