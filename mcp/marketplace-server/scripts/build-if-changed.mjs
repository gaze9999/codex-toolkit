import { createHash } from 'node:crypto';
import { existsSync, readFileSync, writeFileSync, mkdirSync, lstatSync, readdirSync } from 'node:fs';
import { resolve, dirname, join, relative, isAbsolute, sep } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';

export const deploymentFiles = ['LICENSE', 'api/mcp.mjs', 'api/oauth.mjs', 'auth.mjs', 'catalog.mjs', 'data/catalog.json', 'handler.mjs', 'package-lock.json', 'package.json', 'vercel.json'];
export function snapshotInputs(root, names = deploymentFiles) {
  const base = resolve(root);
  const files = {};
  for (const name of [...new Set(names)].sort()) {
    const file = resolve(base, name);
    const local = relative(base, file);
    if (!local || isAbsolute(local) || local === '..' || local.startsWith('..' + sep)) throw new Error('Input leaves project');
    let current = base;
    for (const part of local.split(sep)) {
      current = join(current, part);
      if (lstatSync(current).isSymbolicLink()) throw new Error('Symlink input');
    }
    if (!lstatSync(file).isFile()) throw new Error('Input is not a file');
    files[name] = createHash('sha256').update(readFileSync(file)).digest('hex');
  }
  const fingerprint = createHash('sha256').update(JSON.stringify(files)).digest('hex');
  return { schemaVersion: 1, fingerprint, files };
}
export function needsBuild(current, previous) {
  return previous?.schemaVersion !== 1 || previous?.fingerprint !== current.fingerprint || JSON.stringify(previous?.files) !== JSON.stringify(current.files);
}
function run(root, args) {
  const child = spawnSync(process.execPath, args, { cwd: root, stdio: 'inherit' });
  if (child.error || child.status !== 0) throw new Error('Build step failed');
}
if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const root = fileURLToPath(new URL('../', import.meta.url));
  const mode = process.argv[2] ?? '--check';
  if (!['--check', '--build'].includes(mode)) throw new Error('Use --check or --build');
  if (mode === '--build') run(root, ['scripts/snapshot.mjs']);
  const input = snapshotInputs(root);
  const state = join(root, '.state', 'last-build.json');
  const previous = existsSync(state) ? JSON.parse(readFileSync(state, 'utf8')) : null;
  if (!needsBuild(input, previous)) console.log(JSON.stringify({ status: 'unchanged', fingerprint: input.fingerprint }));
  else if (mode === '--check') console.log(JSON.stringify({ status: 'changed', fingerprint: input.fingerprint }));
  else {
    const tests = readdirSync(join(root, 'test')).filter(name => name.endsWith('.test.mjs')).sort().map(name => 'test/' + name);
    if (!tests.length) throw new Error('No acceptance checks');
    run(root, ['--test', ...tests]);
    if (snapshotInputs(root).fingerprint !== input.fingerprint) throw new Error('Build inputs changed during checks');
    mkdirSync(dirname(state), { recursive: true });
    writeFileSync(state, JSON.stringify(input, null, 2) + '\n');
    console.log(JSON.stringify({ status: 'built', fingerprint: input.fingerprint, deployed: false }));
  }
}
