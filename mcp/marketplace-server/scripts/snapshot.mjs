import { execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { mkdirSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('../../../', import.meta.url));
const git = (...args) => execFileSync('git', ['-C', root, ...args], { maxBuffer: 16 * 1024 * 1024 });
const revision = git('rev-parse', 'HEAD').toString().trim();
const read = path => git('show', revision + ':' + path).toString('utf8');
const catalog = JSON.parse(read('plugins/catalog.json'));
const plugins = catalog.bundles.filter(bundle => bundle.status === 'ready').map(bundle => {
  const manifest = JSON.parse(read('plugins/' + bundle.id + '/plugin.json'));
  return { id: manifest.name, version: manifest.version, description: manifest.description, skills: bundle.skills };
});
const paths = git('ls-tree', '-r', '--name-only', revision, '--', 'skills/').toString().trim().split('\n');
const files = {};
for (const path of paths) {
  if (!/^skills\/[a-z0-9-]+\/(SKILL\.md|references\/.+\.md)$/.test(path)) continue;
  const text = read(path);
  if (Buffer.byteLength(text) > 256 * 1024) throw new Error('Oversized source: ' + path);
  files[path] = { text, sha256: createHash('sha256').update(text).digest('hex') };
}
const skills = Object.keys(files).filter(path => path.endsWith('/SKILL.md')).map(path => {
  const id = path.split('/')[1];
  const description = files[path].text.match(/^description:\s*(.+)$/m)?.[1] ?? id;
  return { id, description, plugins: plugins.filter(plugin => plugin.skills.includes(id)).map(plugin => plugin.id) };
});
const output = new URL('../data/catalog.json', import.meta.url);
mkdirSync(new URL('../data/', import.meta.url), { recursive: true });
writeFileSync(output, JSON.stringify({ repository: 'https://github.com/gaze9999/codex-toolkit', revision, plugins, skills, files }));
console.log(JSON.stringify({ revision, plugins: plugins.length, skills: skills.length, files: Object.keys(files).length }));
