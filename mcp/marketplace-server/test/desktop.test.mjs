import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, mkdirSync, writeFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { execFileSync, spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

test('Desktop alignment accepts exact bytes and rejects drift and wrong target', () => {
  const root = mkdtempSync(join(tmpdir(), 'marketplace-alignment-'));
  try {
    const repo = join(root, 'repo');
    const cache = join(root, 'cache');
    const dist = join(repo, 'marketplace/plugins/example');
    const installed = join(cache, 'example/1.0.0');
    mkdirSync(dist, { recursive: true });
    mkdirSync(installed, { recursive: true });
    writeFileSync(join(dist, 'plugin.json'), '{}\n');
    writeFileSync(join(installed, 'plugin.json'), '{}\n');
    const git = (...args) => execFileSync('git', ['-C', repo, ...args]);
    git('init', '--quiet');
    git('add', '.');
    git('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', '-c', 'commit.gpgsign=false', 'commit', '--quiet', '-m', 'fixture');
    const revision = git('rev-parse', 'HEAD').toString().trim();
    const snapshot = join(root, 'catalog.json');
    writeFileSync(snapshot, JSON.stringify({ repository: 'https://github.com/gaze9999/codex-toolkit', revision, plugins: [{ id: 'example', version: '1.0.0' }] }));
    const run = target => spawnSync(process.execPath, [fileURLToPath(new URL('../scripts/verify-desktop.mjs', import.meta.url)), repo, cache, snapshot, target], { encoding: 'utf8' });
    assert.equal(run(revision).status, 0);
    assert.notEqual(run('0'.repeat(40)).status, 0);
    writeFileSync(join(installed, 'plugin.json'), 'changed');
    assert.notEqual(run(revision).status, 0);
    writeFileSync(join(installed, 'plugin.json'), '{}\n');
    writeFileSync(join(installed, 'extra.md'), 'extra');
    assert.notEqual(run(revision).status, 0);
  } finally { rmSync(root, { recursive: true, force: true }); }
});
