# Review checks

## Comments

- Keep information the source cannot express clearly: null versus empty semantics, precedence, side effects, caller contracts, platform constraints and non-obvious ordering. Apply the owning project's comment syntax and terminology.
- Flag comments that only repeat names, signatures or surrounding markup. Keep required directives and useful section boundaries. Record commented-out behavior separately and look for a confirmed retention decision before proposing deletion.

## Call chains and forwarding

- Start at the actual event or external entry point. Trace caller, state ownership, mapping and side effects. A method that adds validation, cancellation, error translation, caching, state, a public contract or a boundary check has a responsibility.
- Propose removing a private forwarding layer only if every caller, receiver, ordering guarantee and observable behavior stays equivalent. Check any affected request parameters, field sources, request counts and response handling against the project evidence. Route contract differences to their owner.
- For Angular-specific component, service and template ownership, use [Angular code maintainability](https://github.com/gaze9999/codex-toolkit/blob/main/skills/angular-development/references/code-maintainability.md).

## Orphans, exports and members

- Reconcile the graph with real entry points, test/bootstrap registration, barrel re-exports and external package consumers. Distinguish a same-file reference from an importing consumer.
- Inspect reads, writes, bindings, inheritance, overrides, callbacks, registration, serialization, computed names and reflective access. Public interfaces can have callers outside the scan root. A write or a spelling match alone is weak evidence.
- Apply retained scopes before producing findings. Record dynamic imports, unresolved aliases, decorator registration, reflection and partial coverage as needs-decision cases. Check bindings against the actual component template.

## Duplicate regions and complexity

- Compare detected regions side by side. Confirm shared behavior, naming intent, state ownership and change cadence. Visually similar regions can encode different domain rules. Avoid moving unrelated responsibilities into one class or helper.
- Compare branching and length against the project's existing thresholds. If ESLint is installed locally and the project config accepts the core rules, use its existing runner with scoped paths and `--rule` overrides for `complexity` and `max-lines-per-function` at the confirmed thresholds. Run without `--fix`. Keep failed or unsupported lint checks separate from token-based counts.
- Identify the concrete maintenance impact, such as duplicated validation paths, uncertain side effects or missing coverage. Shorter code or a lower score alone does not establish an improvement.
