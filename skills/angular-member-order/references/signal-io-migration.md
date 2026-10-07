# Signal Input and Output Migration

Use this reference only when the user explicitly requests Angular signal inputs or outputs. Verify that the target Angular version supports the selected APIs before editing. Do not upgrade Angular or TypeScript for this migration.

## Preserve the public binding contract

- Replace eligible `@Input` declarations with property-initializer calls to `input()` or `input.required()`
- Replace eligible `@Output` plus `EventEmitter` declarations with `output()`
- Preserve every external property name, event name, alias, payload type, default value, and parent binding
- Remove `Input`, `Output`, and `EventEmitter` imports only when no remaining declaration uses them
- Convert input/output pairs to `model()` only when the user explicitly requests it
- Do not add wrappers around `input()` or `output()` because Angular recognizes these APIs only in supported property initializer positions

Use `input.required<T>()` only when an authoritative contract or every valid caller proves that the input is required. A missing default or a non-null type alone is not proof. Otherwise preserve optionality and the existing default with `input<T>(defaultValue)`.

## Update consumers inside the component

Signal inputs are read by calling them. Update all affected class code, computed state, lifecycle code, and templates from property reads such as `visible` or `this.visible` to `visible()` or `this.visible()` as appropriate.

Do not write to an `InputSignal`. If the component currently mutates an input, identify the real local owner and introduce the smallest local writable state needed to preserve behavior. Keep the external input contract unchanged.

Output bindings in parent templates remain unchanged. Existing `.emit(value)` calls remain valid with `output()`, but code that relies on `EventEmitter`-specific `complete`, `error`, or Observable behavior requires a separate compatibility decision rather than a mechanical replacement.

## Handle non-mechanical inputs

Treat these as behavior-sensitive cases:

- Setter inputs
- Aliased inputs or outputs
- Input transforms
- `ngOnChanges` or `SimpleChanges` logic
- Direct child-input assignment through `ViewChild`
- Tests that assign directly to component input properties
- Inputs involved in two-way binding
- Inherited inputs/outputs, overrides, and public consumers outside the component's template

For a setter input, separate the incoming signal from derived local state. Reproduce side effects with the smallest supported reactive or lifecycle mechanism only after verifying timing, initialization, and cleanup. Do not place side effects inside an input transform. If equivalent behavior cannot be demonstrated, leave that declaration unchanged and report the blocker instead of forcing the migration.

Update direct programmatic input writes and tests through the framework-supported input-setting path when needed. Preserve the existing two-way binding names even when input and output declarations become signal-based.

## Verify the migration

In addition to the member-ordering checks:

- Search the affected scope for remaining `@Input`, `@Output`, and `EventEmitter` usages and classify intentional exceptions
- Search for stale reads of converted input members that omit `()`
- Verify affected templates compile
- Verify output payload types and `.emit()` call sites
- Run the narrowest applicable Angular type or compile check and any focused tests that cover setter, lifecycle, and two-way binding behavior
- Report intentional legacy declarations, blocked conversions, and checks not run
