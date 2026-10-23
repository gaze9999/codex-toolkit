import { getAuthorization } from '../auth.mjs';

export function createMetadataEndpoint(resolveAuthorization = getAuthorization) {
  return function metadata(req, res) {
    if (req.method !== 'GET') { res.writeHead(405); return res.end(); }
    try {
      const body = JSON.stringify(resolveAuthorization().metadata);
      res.writeHead(200, { 'content-type': 'application/json', 'cache-control': 'no-store' });
      res.end(body);
    } catch {
      res.writeHead(503, { 'content-type': 'application/json', 'cache-control': 'no-store' });
      res.end(JSON.stringify({ error: 'Authentication is not configured' }));
    }
  };
}
export default createMetadataEndpoint();
