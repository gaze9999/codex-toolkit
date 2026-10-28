import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, writeFileSync, rmSync, realpathSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve, dirname, basename } from 'node:path';
import { snapshotInputs, needsBuild } from '../scripts/build-if-changed.mjs';

function cleanup(root) {
  const actual = realpathSync(root);
  assert.equal(dirname(actual), realpathSync(tmpdir()));
  assert.match(basename(actual), /^mcp-build-/);
  rmSync(actual, { recursive: true });
}

test('unchanged bytes skip a build; edits, deletions and new inputs are detected', () => {
  const root = mkdtempSync(join(tmpdir(), 'mcp-build-'));
  try {
    writeFileSync(join(root, 'a'), 'alpha');
    const before = snapshotInputs(root, ['a']);
    assert.equal(needsBuild(before, before), false);
    assert.equal(needsBuild(before, null), true);
    writeFileSync(join(root, 'a'), 'beta');
    assert.equal(needsBuild(snapshotInputs(root, ['a']), before), true);
    writeFileSync(join(root, 'b'), 'alpha');
    assert.equal(needsBuild(snapshotInputs(root, ['a', 'b']), before), true);
    rmSync(join(root, 'a'));
    assert.throws(() => snapshotInputs(root, ['a']));
  } finally { cleanup(root); }
});
test('input order is stable, modified state fails closed, and traversal is rejected', () => {
  const root = mkdtempSync(join(tmpdir(), 'mcp-build-'));
  try {
    writeFileSync(join(root, 'a'), 'alpha');
    writeFileSync(join(root, 'b'), 'beta');
    const before = snapshotInputs(root, ['b', 'a']);
    assert.deepEqual(before, snapshotInputs(root, ['a', 'b']));
    assert.equal(needsBuild(before, { ...before, files: {} }), true);
    assert.throws(() => snapshotInputs(root, ['../escape']));
    assert.throws(() => snapshotInputs(root, ['.']));
  } finally { cleanup(root); }
});
