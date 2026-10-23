import { randomUUID } from 'node:crypto';
import { handler } from '../handler.mjs';
import { getAuthorization } from '../auth.mjs';
const methods = new Set(['initialize', 'notifications/initialized', 'tools/list', 'tools/call', 'ping']);
const tools = new Set(['list_plugins', 'search_skills', 'read_skill', 'read_skill_reference']);
export function createEndpoint(resolveAuthorization = getAuthorization, processRequest = handler, log = entry => console.info(JSON.stringify(entry))) { return async function endpoint(req, res) {
  const trace = { event: 'mcp_request', requestId: randomUUID(), phase: 'request' };
  const started = performance.now();
  const emit = outcome => {
    try { log({ ...trace, outcome, status: res.statusCode, durationMs: Math.round(performance.now() - started) }); }
    catch { /* Diagnostics must not change the request result. */ }
  };
  res.setHeader('x-mcp-request-id', trace.requestId);
  res.once('finish', () => emit('finished'));
  res.once('close', () => { if (!res.writableFinished) emit('disconnected'); });
  emit('received');
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
  trace.phase = 'authorization';
  let denied;
  try { denied = await authorization.authorize(authHeaders); }
  catch {
    res.writeHead(503, { 'content-type': 'application/json', 'cache-control': 'no-store' });
    return res.end(JSON.stringify({ error: 'Authentication is unavailable' }));
  }
  if (denied) {
    res.writeHead(denied.status, Object.fromEntries(denied.headers));
    return res.end(await denied.text());
  }
  trace.phase = 'body';
  let body;
  try {
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
  } catch {
    if (!res.destroyed) {
      res.writeHead(400, { 'content-type': 'application/json' });
      res.end(JSON.stringify({ error: 'Invalid request body' }));
    }
    return;
  }
  try {
    const parsed = JSON.parse(body);
    trace.method = methods.has(parsed?.method) ? parsed.method : 'other';
    if (parsed?.method === 'tools/call') trace.tool = tools.has(parsed.params?.name) ? parsed.params.name : 'other';
  } catch { /* MCP owns protocol validation. */ }
  const headers = new Headers();
  for (const [key, value] of Object.entries(req.headers)) if (value !== undefined) headers.set(key, Array.isArray(value) ? value.join(', ') : value);
  try {
    trace.phase = 'handler';
    const response = await processRequest(new Request('https://' + host + '/api/mcp', { method: req.method, headers, ...(body !== undefined ? { body } : {}) }));
    trace.phase = 'response';
    const payload = Buffer.from(await response.arrayBuffer());
    trace.bytes = payload.length;
    const text = payload.toString('utf8');
    const frames = response.headers.get('content-type')?.includes('text/event-stream')
      ? text.split('\n').filter(line => line.startsWith('data:')).map(line => line.slice(5)) : [text];
    for (const value of frames) {
      try {
        const message = JSON.parse(value);
        if (Number.isInteger(message.error?.code)) trace.rpcCode = message.error.code;
        if (message.result?.isError === true) trace.toolError = true;
      } catch { /* Ignore non-JSON frames without logging content. */ }
    }
    res.writeHead(response.status, Object.fromEntries(response.headers));
    res.end(payload);
  } catch {
    res.writeHead(500, { 'content-type': 'application/json' });
    res.end(JSON.stringify({ error: 'MCP request failed' }));
  }
}; }
export default createEndpoint();
