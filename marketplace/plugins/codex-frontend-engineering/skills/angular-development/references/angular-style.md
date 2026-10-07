# Angular layout and compact code reference

Load for an authorized Angular implementation or style review. Adapt to the actual
project versions, formatter, state owner and component contracts before copying.
This is a reference, not a migration instruction or a required global read.

For authorized call-chain or Model changes, read [code maintainability](code-maintainability.md).

## Compatibility and ownership

The complete example uses Angular 17+ standalone components, stable Signals and
built-in control flow. Select the compatible TypeScript/Node versions from
[Angular's version table](https://angular.dev/reference/versions). Existing NgModule,
RxJS, forms and decorator I/O patterns remain valid; change them only in scope.

The list is a local fixture. A production feature keeps shared state and request
lifecycle with its existing Service/store, view interaction with the Component,
and substantial pure business rules with the feature's rules/mapper/projection.
The example performs no persistence or API request.

## One component, grouped by responsibility

Keep consecutive members together within each group and one blank line between
groups. Group headings follow the project's comment language. Public class members
are explicit; private boundaries stay private. Derived state comes from its owner,
and immutable updates keep the Signals' reference changes observable.

```ts
import { ChangeDetectionStrategy, Component, computed, signal } from '@angular/core';

/** 本機工作項目, id 是固定識別值, done 表示是否完成 */
interface Task {
  id: number;
  title: string;
  done: boolean;
}

@Component({
  selector: 'app-task-board',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <section class="board" aria-labelledby="task-heading">
      <header class="heading">
        <h2 id="task-heading">工作清單</h2>
        <p role="status">{{ visible().length }} / {{ tasks().length }} 筆</p>
      </header>

      <div class="filters">
        <label for="task-query">搜尋工作</label>
        <input id="task-query" type="search" [value]="query()"
          [maxLength]="queryLimit" (input)="onQuery($event)" />
        <button type="button" [disabled]="!query()" (click)="clearQuery()">清除搜尋</button>
      </div>

      <ul class="tasks">
        @for (task of visible(); track task.id) {
          <li>
            <label class="task">
              <input type="checkbox" [checked]="task.done" (change)="toggle(task.id)" />
              <span [class.done]="task.done">{{ task.title }}</span>
              <span class="badge">{{ task.done ? '已完成' : '待處理' }}</span>
            </label>
          </li>
        } @empty {
          <li class="empty">沒有符合搜尋的工作</li>
        }
      </ul>
    </section>
  `,
  styles: `
    :host { display: block; }
    .board { max-inline-size: 48rem; margin-inline: auto; padding: 1rem; }
    .heading { display: flex; flex-wrap: wrap; align-items: baseline; gap: .5rem 1rem; }
    .heading h2 { margin: 0; }
    .heading p { margin-inline-start: auto; }
    .filters { display: grid; grid-template-columns: auto minmax(0, 1fr) auto;
      align-items: center; gap: .5rem; }
    .filters input { min-inline-size: 0; }
    .tasks { display: grid; gap: .5rem; padding: 0; list-style: none; }
    .task { display: grid; grid-template-columns: auto minmax(0, 1fr) auto;
      align-items: start; gap: .5rem; padding: .75rem; border: 1px solid #777; border-radius: .5rem; }
    .task > span { overflow-wrap: anywhere; }
    .task input { margin-block-start: .2rem; }
    .done { text-decoration: line-through; }
    .badge { font-size: .875rem; }
    .empty { padding: .75rem; }
    :is(input, button):focus-visible { outline: 2px solid currentColor; outline-offset: 3px; }
    @media (max-width: 36rem) {
      .filters { grid-template-columns: minmax(0, 1fr) auto; }
      .filters label { grid-column: 1 / -1; }
      .task { grid-template-columns: auto minmax(0, 1fr); }
      .badge { grid-column: 2; }
    }
  `,
})
export class TaskBoardComponent {
  /** 畫面常數 */
  public readonly queryLimit = 120;

  /** 畫面狀態與衍生資料 */
  public readonly query = signal('');
  public readonly tasks = signal<readonly Task[]>([
    { id: 1, title: '核對 Plugin 來源映射', done: !1 },
    { id: 2, title: '讀回套件 checksum', done: !0 },
  ]);
  public readonly visible = computed(() => {
    const query = this.query().trim().toLocaleLowerCase('zh-TW');
    return query
      ? this.tasks().filter(({ title }) => title.toLocaleLowerCase('zh-TW').includes(query))
      : this.tasks();
  });

  /** 搜尋流程 */
  public onQuery({ target }: Event): void {
    if (!(target instanceof HTMLInputElement)) return;
    this.query.set(target.value.slice(0, this.queryLimit));
  }
  public clearQuery(): void { return void this.query.set(''); }

  /** 完成狀態流程 */
  public toggle(id: Task['id']): void {
    this.tasks.update(tasks => tasks.map(task => task.id === id ? { ...task, done: !task.done } : task));
  }
}
```

The example uses native labelled controls, a stable `track` identity, visible focus,
a count status, a disabled clear action and an explicit empty state. Grid's
`minmax(0, 1fr)` and logical sizing allow long text to wrap; the narrow layout moves
the status below its title. Repeated component instances need unique heading/input
IDs from the project's existing ID convention.

## Member order and compact expressions

When present, use: static constants → inputs → outputs → view/content references →
public constants/options → public state/forms → accessors → private DI → private
state → constructor → lifecycle → feature event/operation/helper groups → shared
helpers. Keep accessor pairs and overloads adjacent. A helper for one flow stays
with that flow; avoid alphabetical sorting or a rigid public/private method split.

Initializer dependencies take precedence. If a public form initializer uses an
injected FormBuilder, declare that injection before the form. Do not move an
`inject()` call outside an Angular injection context. Keep decorator and comment
ownership, reactive timing and side effects when moving members.

| Intent | Compact example | Preserve |
| --- | --- | --- |
| Nullish default | `const title = record?.title ?? fallback;` | Empty strings, `0` and `false` remain valid |
| Falsy default | `const label = query.trim() \|\| '全部';` | Use only when every falsy result should fall back |
| Conditional value | `const label = done ? '已完成' : '待處理';` | Keep branches short and meaningful |
| Single guard | `if (!id) return;` | Only if `0` is invalid under the actual ID format |
| Conditional effect | `enabled && refresh();` | Keep evaluation order and returned-value semantics |
| Nullish assignment | `cache[key] ??= create();` | Evaluate the factory only when absent |
| Falsy assignment | `options.label \|\|= '未命名';` | Replaces every falsy value, including empty text, `0`, `false` and `NaN` |
| Truthy assignment | `options.enabled &&= available;` | Assign only when the current value is truthy |
| Boolean literal | `signal(!1)` / `signal(!0)` | Follow the project's lint rules and user preference |
| Undefined value | `const value = condition ? result : void 0;` | Keep expression precedence; do not replace type/member names |
| Void callback | `const close = (): void => void dialog.close();` | Suitable only when the caller intentionally discards the return |
| Explicit async effect | `public async save(): Promise<void> { await this.store.save(); }` | Retain awaited errors and the existing caller's error handling |

Infer clear, stable value return types; keep public interface/overload constraints.
Functions without a result use `: void`, async functions use `Promise<void>`.
Do not discard a meaningful result or an unhandled Promise just to shorten code.
Do not add `public` to interfaces, types, setters' parameters or JavaScript.

Use supported native APIs when they clarify the authorized change. Check
TypeScript `target`/`lib`, Browserslist and runtime support before using `at()`,
`toSorted()`, `Object.groupBy()` or newer Set operations. Preserve mutation,
reference identity, order and error behavior; compilation alone does not prove
browser support. Do not add a helper solely to wrap another call or move private
view behavior into a Service to reduce line count.

## Single-statement guards and logical assignment

Omit braces for a clear single-statement `if`, including an early `return` or
`throw`. Put `return` and its expression on the same line. Keep braces for multiple
statements, ambiguous nested `if`/`else`, scoped declarations or a branch whose
comments need a block. Do not remove validation or change its ordering to flatten
the function. Avoid an `else` after a branch that already returns when the remaining
flow is clearer at the same indentation.

```js
function normalizeOptions(options, available) {
  if (options == null) throw new TypeError('Missing options');
  const result = { ...options };
  result.limit ??= 100;
  result.label ||= '未命名';
  result.enabled &&= available;
  return result;
}
```

This example shallow-copies a plain options object before assignment. A limit of
`0` survives `??=`, an empty label is replaced by `||=`, and an existing disabled
flag remains disabled under `&&=`. `??=` tests only null/undefined; `||=` tests
falsiness; `&&=` tests truthiness. The right operand and assignment run only when
needed. Preserve property getters/setters and side effects: the left reference is
evaluated once, so these operators are not a blind replacement for repeated reads.
They assign through ordinary properties, not Angular Signal setters; keep
`signal.set()` / `signal.update()` for reactive state. Check the project's actual
TypeScript and browser support before adopting them.

## Large numbers and compact display

Use scientific notation for clear equivalent constants or quantities whose
accepted precision is approximate. Use numeric separators when individual digits
matter. Keep units in the name or field documentation.

```js
const timeoutMs = 3e4;          // 30000 milliseconds
const largeCountThreshold = 1e6;
const estimatedCount = 1.2e9;   // Estimate at the accepted precision
const exactCount = 1_234_567_890;
const exactLargeInteger = 9_007_199_254_740_993n;

function formatEstimate(value) {
  if (value == null) return '--';
  if (!Number.isFinite(value)) return '無效數值';
  return Math.abs(value) < largeCountThreshold
    ? String(value)
    : `約 ${value.toExponential(2)}`;
}
```

`3e4` and `30_000` represent the same Number. Writing an exponent does not improve
Number precision or authorize rounding an exact value. `toExponential(2)` returns
a display string with two fractional significand digits, three significant digits
in total; keep the original value for computation, comparison and persistence.
An approximate label belongs only to data that permits approximation.

Exact integers outside `Number.MAX_SAFE_INTEGER` need a compatible BigInt or
string field. Construct them from an integer literal or exact string, not an
already-rounded Number. BigInt literals have no exponent form; use `10n ** 18n`
when appropriate, and preserve the API's serialization format. Monetary decimal
precision follows the existing integer-minor-unit or decimal representation.
Do not shorten IDs, amounts or exact counts by dropping significant digits.

## Acceptance when adapting

Read back the diff, then run the affected project's type/template check. Exercise
query updates, clear/disabled state, checkbox changes, empty results, narrow layout,
long titles and keyboard focus. A copied reference is not evidence of a compiled
or browser-tested application. Use the existing formatter without reformatting
unrelated code.

Sources: [Signals](https://angular.dev/guide/signals),
[control flow](https://angular.dev/guide/templates/control-flow),
[injection context](https://angular.dev/guide/di/dependency-injection-context),
[assignment operators](https://tc39.es/ecma262/multipage/ecmascript-language-expressions.html#sec-assignment-operators),
[if statements](https://tc39.es/ecma262/multipage/ecmascript-language-statements-and-declarations.html#sec-if-statement),
[numeric literals](https://tc39.es/ecma262/multipage/ecmascript-language-lexical-grammar.html#sec-literals-numeric-literals),
[exponential display](https://tc39.es/ecma262/multipage/numbers-and-dates.html#sec-number.prototype.toexponential)
