import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { once } from 'node:events';
import { mkdir, copyFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const [python, playwrightPath, threePath, output, browserPath] = process.argv.slice(2);
if (!browserPath) throw new Error('Provide python, playwright module, three root, new output directory and browser executable');
await mkdir(output, { recursive: false });
await mkdir(path.join(output, 'vendor'));
const assets = fileURLToPath(new URL('../assets/', import.meta.url));
for (const file of ['example.html', 'three-scene.mjs']) await copyFile(path.join(assets, file), path.join(output, file));
for (const file of ['three.module.js', 'three.core.js']) await copyFile(path.join(threePath, 'build', file), path.join(output, 'vendor', file));
const { chromium } = await import(pathToFileURL(playwrightPath).href);
const source = 'import json,sys\nfrom codex_visual_runtime.core import Workspace,Previews\np=Previews(Workspace(sys.argv[1]))\ntry:\n print(json.dumps(p.start("example.html",["example.html","three-scene.mjs","vendor/three.module.js","vendor/three.core.js"])),flush=True)\n sys.stdin.readline()\nfinally:\n p.close()';
const server = spawn(python, ['-c', source, path.resolve(output)], { stdio: ['pipe', 'pipe', 'pipe'], windowsHide: true });
const exited = once(server, 'exit');
let browser;
let errors = [];
try {
  const job = await new Promise((resolve, reject) => {
    let pending = '';
    const timeout = setTimeout(() => reject(new Error('Preview readiness timed out')), 10000);
    server.once('error', reject);
    server.stderr.on('data', data => errors.push(data.toString()));
    server.stdout.on('data', data => {
      pending += data.toString();
      if (pending.includes('\n')) { clearTimeout(timeout); resolve(JSON.parse(pending.split('\n')[0])); }
    });
  });
  assert.equal(job.status, 'ready');
  browser = await chromium.launch({ executablePath: browserPath, headless: true });
  const context = await browser.newContext({ viewport: { width: 1100, height: 900 }, deviceScaleFactor: 2 });
  const page = await context.newPage();
  page.on('pageerror', error => errors.push(error.message));
  await page.goto(job.url, { timeout: 15000 });
  await page.waitForFunction(() => window.visualExample?.getState().frames > 2);
  assert.equal(await page.locator('#rows tr').count(), 3);
  assert.deepEqual(await page.locator('#rows td:nth-child(2)').allTextContents(), ['22', '28', '24']);
  for (let i = 0; i < 3; i++) {
    await page.locator('#dispose').click();
    assert.equal((await page.evaluate(() => window.visualExample.getState())).active, false);
    await page.locator('#mount').click();
  }
  const resources = await page.evaluate(() => window.visualExample.getState().disposedResources);
  assert.equal(resources, 18);
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.waitForTimeout(100);
  const before = await page.evaluate(() => window.visualExample.getState().frames);
  await page.waitForTimeout(120);
  assert.equal(await page.evaluate(() => window.visualExample.getState().frames), before);
  assert.equal(await page.locator('.sun').evaluate(element => getComputedStyle(element).animationName), 'none');
  await page.setViewportSize({ width: 390, height: 844 });
  await page.waitForTimeout(100);
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
  const dimensions = await page.locator('canvas').evaluate(canvas => ({ width: canvas.width, css: canvas.clientWidth }));
  assert.equal(dimensions.width, dimensions.css * 2);
  await page.screenshot({ path: path.join(output, 'mobile.png'), fullPage: true });
  await page.setViewportSize({ width: 1100, height: 900 });
  await page.screenshot({ path: path.join(output, 'desktop.png'), fullPage: true });
  await page.locator('#dispose').click();
  assert.equal(await page.evaluate(() => window.visualExample.getState().disposedResources), 24);
  const summary = { status: 'pass', three: '0.187.0', browser: await browser.version(), checks: ['data-table', 'webgl-render', 'three-remounts', 'resource-disposal', 'reduced-motion', 'mobile-overflow', 'DPR-resize'], errors };
  assert.deepEqual(errors, []);
  await writeFile(path.join(output, 'result.json'), JSON.stringify(summary, null, 2));
  console.log(JSON.stringify(summary));
} finally {
  if (browser) await browser.close();
  server.stdin.end('\n');
  await exited;
}
