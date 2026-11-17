// Headless Chrome or Edge through the DevTools protocol, using Node's own WebSocket; no browser automation package is needed.
import { spawn, spawnSync } from 'node:child_process';
import { existsSync } from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

/** Installed browser candidates per platform; an explicit path or CHROME_PATH wins. */
export function browserCandidates(platform = process.platform, env = process.env) {
  if (platform === 'darwin') return [
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge',
    '/Applications/Chromium.app/Contents/MacOS/Chromium',
  ];
  if (platform === 'win32') return [env.PROGRAMFILES, env['PROGRAMFILES(X86)'], env.LOCALAPPDATA].filter(Boolean).flatMap(base => [
    path.join(base, 'Google/Chrome/Application/chrome.exe'),
    path.join(base, 'Microsoft/Edge/Application/msedge.exe'),
  ]);
  return ['google-chrome', 'google-chrome-stable', 'chromium', 'chromium-browser', 'microsoft-edge']
    .map(name => spawnSync('which', [name], { encoding: 'utf8' }).stdout?.trim()).filter(Boolean);
}

export function findBrowser(explicit, env = process.env) {
  const chosen = explicit ?? env.CHROME_PATH;
  if (chosen) {
    if (!existsSync(chosen)) throw new Error(`找不到瀏覽器: ${chosen}`);
    return chosen;
  }
  const found = browserCandidates(process.platform, env).find(file => existsSync(file));
  if (!found) throw new Error('找不到 Chrome 或 Edge, 請用 --chrome 或 CHROME_PATH 指定');
  return found;
}

class Session {
  #socket; #next = 1; #pending = new Map(); #listeners = new Map();
  constructor(socket) {
    this.#socket = socket;
    socket.addEventListener('message', event => {
      const message = JSON.parse(String(event.data));
      if (message.id) {
        const waiter = this.#pending.get(message.id);
        this.#pending.delete(message.id);
        if (message.error) waiter?.reject(new Error(`${message.error.message} ${message.error.data ?? ''}`.trim()));
        else waiter?.resolve(message.result);
        return;
      }
      for (const listener of this.#listeners.get(message.method) ?? []) listener(message.params);
    });
    socket.addEventListener('close', () => {
      for (const waiter of this.#pending.values()) waiter.reject(new Error('DevTools 連線已關閉'));
      this.#pending.clear();
    });
  }
  static async open(url) {
    const socket = new WebSocket(url);
    await new Promise((resolve, reject) => {
      socket.addEventListener('open', resolve, { once: true });
      socket.addEventListener('error', () => reject(new Error(`無法連線 DevTools: ${url}`)), { once: true });
    });
    return new Session(socket);
  }
  send(method, params = {}) {
    const id = this.#next++;
    this.#socket.send(JSON.stringify({ id, method, params }));
    return new Promise((resolve, reject) => this.#pending.set(id, { resolve, reject }));
  }
  on(method, listener) {
    this.#listeners.set(method, [...(this.#listeners.get(method) ?? []), listener]);
  }
  once(method) {
    return new Promise(resolve => {
      const listeners = this.#listeners.get(method) ?? [];
      const listener = params => { this.#listeners.set(method, (this.#listeners.get(method) ?? []).filter(item => item !== listener)); resolve(params); };
      this.#listeners.set(method, [...listeners, listener]);
    });
  }
  close() { this.#socket.close(); }
}

const withTimeout = (promise, ms, message) => {
  let timer;
  return Promise.race([promise, new Promise((_, reject) => { timer = setTimeout(() => reject(new Error(message)), ms); })]).finally(() => clearTimeout(timer));
};

/** Load the page, run window.__componentTest.start() and return its results with console errors; the browser is always closed. */
export async function runPage({ browser, profile, page, timezone, timeoutMs, caseTimeoutMs }) {
  const child = spawn(browser, [
    '--headless=new', '--remote-debugging-port=0', `--user-data-dir=${profile}`, '--no-first-run', '--no-default-browser-check',
    '--disable-extensions', '--disable-background-networking', '--disable-component-update', '--allow-file-access-from-files', 'about:blank',
  ], { stdio: ['ignore', 'ignore', 'pipe'] });
  const exited = new Promise(resolve => child.once('exit', resolve));
  const consoleErrors = [];
  let session;
  try {
    let stderr = '';
    const endpoint = await withTimeout(new Promise((resolve, reject) => {
      child.stderr.on('data', chunk => {
        stderr += chunk;
        const match = stderr.match(/DevTools listening on (ws:\/\/\S+)/);
        if (match) resolve(match[1]);
      });
      child.once('error', reject);
      child.once('exit', code => reject(new Error(`瀏覽器提前結束 (${code})\n${stderr.slice(-2000)}`)));
    }), 30000, '瀏覽器沒有在 30 秒內開啟 DevTools');
    const port = new URL(endpoint).port;
    const version = (await (await fetch(`http://127.0.0.1:${port}/json/version`)).json()).Browser;
    const target = (await (await fetch(`http://127.0.0.1:${port}/json/list`)).json()).find(item => item.type === 'page');
    if (!target) throw new Error('瀏覽器沒有可用的分頁');
    session = await Session.open(target.webSocketDebuggerUrl);
    session.on('Runtime.consoleAPICalled', params => {
      if (params.type === 'error' || params.type === 'assert') consoleErrors.push(params.args.map(arg => arg.value ?? arg.description ?? '').join(' ').slice(0, 2000));
    });
    session.on('Runtime.exceptionThrown', params => consoleErrors.push(String(params.exceptionDetails.exception?.description ?? params.exceptionDetails.text).slice(0, 2000)));
    await session.send('Runtime.enable');
    await session.send('Page.enable');
    await session.send('Emulation.setTimezoneOverride', { timezoneId: timezone });
    const loaded = session.once('Page.loadEventFired');
    await session.send('Page.navigate', { url: pathToFileURL(page).href });
    await withTimeout(loaded, 60000, '測試頁沒有在 60 秒內載入');
    /** Read from the loaded test page, so the report shows the agent and time zone the cases ran under rather than the requested values. */
    const observed = (await session.send('Runtime.evaluate', {
      expression: '({ userAgent: navigator.userAgent, timezone: Intl.DateTimeFormat().resolvedOptions().timeZone })', returnByValue: true,
    })).result?.value ?? {};
    const evaluated = await withTimeout(session.send('Runtime.evaluate', {
      expression: `globalThis.__componentTest ? globalThis.__componentTest.start({ caseTimeoutMs: ${Number(caseTimeoutMs)} }) : Promise.reject(new Error('測試頁沒有載入 @component-test/harness'))`,
      awaitPromise: true, returnByValue: true,
    }), timeoutMs, `測試沒有在 ${timeoutMs / 1000} 秒內完成`);
    if (evaluated.exceptionDetails) throw new Error(evaluated.exceptionDetails.exception?.description ?? evaluated.exceptionDetails.text);
    return { version, userAgent: observed.userAgent ?? null, timezone: observed.timezone ?? null, results: evaluated.result.value, consoleErrors };
  } finally {
    session?.close();
    child.kill();
    await withTimeout(exited, 10000, '瀏覽器沒有在 10 秒內結束').catch(() => child.kill('SIGKILL'));
  }
}
