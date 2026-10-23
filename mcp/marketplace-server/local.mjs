import { createServer } from 'node:http';
import endpoint from './api/mcp.mjs';
import metadata from './api/oauth.mjs';

createServer((req, res) => {
  const path = new URL(req.url, 'http://localhost').pathname;
  if (['/.well-known/oauth-protected-resource', '/.well-known/oauth-protected-resource/mcp', '/.well-known/oauth-protected-resource/api/mcp'].includes(path)) return metadata(req, res);
  if (path === '/mcp' || path === '/api/mcp') return endpoint(req, res);
  res.writeHead(404);
  res.end();
}).listen(8787, '127.0.0.1', () => console.log('MCP: http://127.0.0.1:8787/mcp'));
