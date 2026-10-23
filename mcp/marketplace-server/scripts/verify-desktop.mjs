import { execFileSync } from 'node:child_process';
import { readFileSync, readdirSync } from 'node:fs';
import { resolve, relative } from 'node:path';
import { createHash } from 'node:crypto';

const [repo, cache, snapshotPath, expectedRevision] = process.argv.slice(2);
if (!repo || !cache || !snapshotPath || !/^[a-f0-9]{40}$/.test(expectedRevision ?? '')) {
  throw new Error('Usage: node verify-desktop.mjs REPO MARKETPLACE_CACHE SNAPSHOT EXPECTED_FULL_COMMIT');
}
const snapshot = JSON.parse(readFileSync(snapshotPath, 'utf8'));
if (snapshot.repository !== 'https://github.com/gaze9999/codex-toolkit' || snapshot.revision !== expectedRevision) {
  throw new Error('Snapshot repository or revision mismatch');
}
const git = (...args) => execFileSync('git', ['-C', repo, ...args], { maxBuffer: 32 * 1024 * 1024 });
const hash = bytes => createHash('sha256').update(bytes).digest('hex');
const errors = [];
let files = 0;
for (const plugin of snapshot.plugins) {
  if (!/^[a-z0-9-]+$/.test(plugin.id) || !/^[a-zA-Z0-9.+-]+$/.test(plugin.version)) throw new Error('Invalid plugin identity');
  const prefix = 'marketplace/plugins/' + plugin.id + '/';
  const paths = git('ls-tree', '-r', '--name-only', expectedRevision, '--', prefix).toString().trim().split('\n').filter(Boolean);
  if (!paths.length) throw new Error('Missing distribution: ' + plugin.id);
  const root = resolve(cache, plugin.id, plugin.version);
  const expected = new Set(paths.map(path => path.slice(prefix.length)));
  for (const path of paths) {
    const name = path.slice(prefix.length);
    try {
      if (hash(readFileSync(resolve(root, name))) !== hash(git('show', expectedRevision + ':' + path))) errors.push(plugin.id + '/' + name + ': content mismatch');
    } catch { errors.push(plugin.id + '/' + name + ': unavailable'); }
    files++;
  }
  try {
    for (const entry of readdirSync(root, { recursive: true, withFileTypes: true })) {
      if (entry.isSymbolicLink()) { errors.push(plugin.id + ': unexpected link'); continue; }
      if (!entry.isFile()) continue;
      const name = relative(root, resolve(entry.parentPath, entry.name)).replaceAll('\\', '/');
      if (!expected.has(name)) errors.push(plugin.id + '/' + name + ': unexpected file');
    }
  } catch { errors.push(plugin.id + ': cache unavailable'); }
}
console.log(JSON.stringify({ revision: expectedRevision, plugins: snapshot.plugins.length, files, errors }, null, 2));
if (errors.length) process.exitCode = 1;
