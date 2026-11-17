import {
  type ApplicationRef,
  type EnvironmentProviders,
  type Provider,
  reflectComponentType,
  type Type,
} from '@angular/core';
import * as angularCore from '@angular/core';
import { bootstrapApplication } from '@angular/platform-browser';

export type CaseStatus = 'passed' | 'failed' | 'error' | 'info';

export interface Assertion {
  label: string;
  pass: boolean;
  actual: unknown;
  expected?: unknown;
}

export interface CaseResult {
  id: string;
  group: string;
  name: string;
  status: CaseStatus;
  assertions: Assertion[];
  observed?: unknown;
  message?: string;
  elapsedMs: number;
}

export interface Mounted<T> {
  ref: ApplicationRef;
  host: T;
  element: HTMLElement;
  settle(): Promise<void>;
  destroy(): void;
}

interface CaseDefinition {
  id: string;
  group: string;
  name: string;
  info: boolean;
  run: (check: Check) => unknown;
}

const definitions: CaseDefinition[] = [];
let currentGroup = '';
let caseTimeoutMs = 15000;

const equal = (left: unknown, right: unknown): boolean => {
  if (Object.is(left, right)) return !0;
  if (typeof left !== 'object' || typeof right !== 'object' || !left || !right) return !1;
  if (Array.isArray(left) !== Array.isArray(right)) return !1;
  const leftKeys = Object.keys(left), rightKeys = Object.keys(right);
  return leftKeys.length === rightKeys.length
    && leftKeys.every(key => Object.prototype.hasOwnProperty.call(right, key) && equal((left as Record<string, unknown>)[key], (right as Record<string, unknown>)[key]));
};

/** Plain JSON copy so results survive the DevTools boundary; functions and cycles become text. */
const plain = (value: unknown): unknown => {
  const seen = new WeakSet<object>();
  try {
    return JSON.parse(JSON.stringify(value, (_key, item: unknown) => {
      if (typeof item === 'undefined') return '(undefined)';
      if (typeof item === 'function') return '(function)';
      if (typeof item === 'object' && item) {
        if (seen.has(item)) return '(circular)';
        seen.add(item);
      }
      return item;
    }) ?? '"(undefined)"');
  } catch (error: unknown) {
    return `(not serializable: ${error instanceof Error ? error.message : String(error)})`;
  }
};

export class Check {
  public readonly assertions: Assertion[] = [];
  public observed: unknown;

  public equal(actual: unknown, expected: unknown, label = 'value'): boolean {
    const pass = equal(actual, expected);
    this.assertions.push({ label, pass, actual: plain(actual), expected: plain(expected) });
    return pass;
  }
  public ok(condition: boolean, label: string, actual?: unknown): boolean {
    this.assertions.push({ label, pass: condition, actual: plain(actual ?? condition), expected: !0 });
    return condition;
  }
  /** Record what was observed without judging it. */
  public observe(value: unknown): void { this.observed = plain(value); }
}

/** Following cases are reported under this group, such as one form or one component. */
export const group = (name: string): void => { currentGroup = name; };

export const test = (id: string, name: string, run: (check: Check) => unknown): void => {
  definitions.push({ id, group: currentGroup, name, info: !1, run });
};

/** An observation case: it records values and never passes or fails. */
export const observe = (id: string, name: string, run: (check: Check) => unknown): void => {
  definitions.push({ id, group: currentGroup, name, info: !0, run });
};

export const wait = (ms: number): Promise<void> => new Promise(resolve => setTimeout(resolve, ms));

/** Without zone.js, select the zoneless provider this Angular version exports; suite providers still follow and may replace it. */
const zonelessProviders = (): EnvironmentProviders[] => {
  if (typeof (globalThis as { Zone?: unknown }).Zone !== 'undefined') return [];
  const api = angularCore as unknown as Record<string, (() => EnvironmentProviders) | undefined>;
  const provide = ['provideZonelessChangeDetection', 'provideExperimentalZonelessChangeDetection'].map(name => api[name]).find(Boolean);
  return provide ? [provide()] : [];
};

/** Bootstrap a standalone host component in its own application under document.body. */
export async function mount<T>(component: Type<T>, providers: Array<Provider | EnvironmentProviders> = []): Promise<Mounted<T>> {
  const selector = reflectComponentType(component)?.selector;
  if (!selector || !/^[a-z][\w-]*$/.test(selector)) throw new Error('mount 需要具有元素 selector 的 standalone 元件');
  const element = document.createElement(selector);
  document.body.appendChild(element);
  const ref = await bootstrapApplication(component, { providers: [...zonelessProviders(), ...providers] });
  const host = ref.components[0].instance as T;
  const settle = async (): Promise<void> => {
    ref.tick();
    await wait(0);
    ref.tick();
  };
  await settle();
  return { ref, host, element: ref.components[0].location.nativeElement as HTMLElement, settle, destroy: () => ref.destroy() };
}

export const query = <E extends Element = HTMLElement>(selector: string): E => {
  const element = document.querySelector<E>(selector);
  if (!element) throw new Error(`找不到元素: ${selector}`);
  return element;
};

/** The text input itself, or the first input inside a wrapper such as a date picker. */
export const input = (selector: string): HTMLInputElement => {
  const element = query(selector);
  return element instanceof HTMLInputElement ? element : query<HTMLInputElement>(`${selector} input`);
};

/** Script-dispatched typing: value, input and blur events; it is not native keyboard or IME evidence. */
export async function typeBlur(selector: string, text: string): Promise<void> {
  const field = input(selector);
  field.focus();
  field.value = text;
  field.dispatchEvent(new Event('input', { bubbles: !0 }));
  field.dispatchEvent(new Event('blur'));
  field.blur();
  await wait(0);
}

export async function click(selector: string): Promise<void> {
  query(selector).click();
  await wait(0);
}

async function runCase(definition: CaseDefinition): Promise<CaseResult> {
  const check = new Check();
  const started = performance.now();
  const base = { id: definition.id, group: definition.group, name: definition.name };
  let timer: ReturnType<typeof setTimeout> | undefined;
  try {
    await Promise.race([
      Promise.resolve().then(() => definition.run(check)),
      new Promise((_resolve, reject) => { timer = setTimeout(() => reject(new Error(`案例超過 ${caseTimeoutMs} ms`)), caseTimeoutMs); }),
    ]);
  } catch (error: unknown) {
    return { ...base, status: 'error', assertions: check.assertions, observed: check.observed,
      message: error instanceof Error ? (error.stack ?? error.message).slice(0, 2000) : String(error), elapsedMs: performance.now() - started };
  } finally {
    clearTimeout(timer);
  }
  const elapsedMs = performance.now() - started;
  if (definition.info) return { ...base, status: 'info', assertions: check.assertions, observed: check.observed, elapsedMs };
  if (!check.assertions.length) return { ...base, status: 'error', assertions: [], observed: check.observed, message: '案例沒有任何判定', elapsedMs };
  return { ...base, status: check.assertions.every(item => item.pass) ? 'passed' : 'failed', assertions: check.assertions, observed: check.observed, elapsedMs };
}

declare global {
  // eslint-disable-next-line no-var
  var __componentTest: { start(options?: { caseTimeoutMs?: number }): Promise<CaseResult[]> } | undefined;
}

/** Cases run one at a time in definition order; one failure or error does not stop later cases. */
globalThis.__componentTest = {
  async start(options = {}) {
    caseTimeoutMs = options.caseTimeoutMs ?? caseTimeoutMs;
    const results: CaseResult[] = [];
    for (const definition of definitions) results.push(await runCase(definition));
    return results;
  },
};
