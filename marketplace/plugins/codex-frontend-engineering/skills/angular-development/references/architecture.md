# Angular Architecture

Start from the affected feature and its callers. Resolve the actual Angular, TypeScript, RxJS and build-tool versions, application entrypoints, compilation targets, providers and relevant project instructions; a mixed-version workspace may contain separate runtimes.

When local evidence leaves a library/API gap, choose an available documentation/search capability that can retrieve the authoritative source for the verified Angular/RxJS package version. Check the returned source and version, and use the project's matching CLI if that is the chosen integration. Submit only public API questions to external services. If a capability is unavailable, use a compatible existing route, or an available development-tool-setup Skill when setup is needed and authorized.

## Trace the behavior before proposing a boundary

- Map the user event through component, form, service/store, request and render. Identify the single owner and lifetime of each persisted or shared state; distinguish derived state from independently mutable flags.
- Follow provider placement and injector scope, including lazy routes, component providers and dynamically loaded elements. Moving a service or provider can change instance identity and lifetime even when the API is unchanged.
- Follow observable subscriptions, cancellation, signal dependencies and asynchronous results across navigation, input changes and teardown. Do not treat Signals and RxJS as interchangeable or assume a newer API exists in the current runtime.
- For Host/custom-element boundaries, inspect both owners: selector, properties/attributes, events and detail, routing/session ownership, shared assets and bundle loading. Local UI success does not establish Host or backend integration.
- For rendering or performance questions, identify the exercised change-detection/render path and actual measurements before recommending memoization, state migration, SSR or hydration changes.

## Choose the smallest useful structure

Keep screen coordination, local form interaction and DOM/lifecycle behavior near the component. Place shared state, request lifetime and API access with the existing feature service/store owner; place reusable pure transformations near their feature. Do not move everything into a service or add wrappers only to reduce component length.

Compare a proposed boundary with the current structure using change coupling, lookup cost, lifetime and testability. Preserve initialization, mutation/reference behavior, event order and public interfaces. A framework upgrade, new state library or cross-owner API change requires task scope that includes it.

## Deliver evidence at the requested level

Describe the requested outcome, confirmed facts, decisions, actual checks and concrete unresolved items. Support comparisons with evidence and applicable conditions, and retain limitations that affect correctness, safety, compatibility, requirements or execution.

For analysis, provide the current flow, concrete problem, viable alternatives and trade-offs, unresolved requirements and a minimal next step; a small Mermaid diagram can clarify ownership. Do not implement when only analysis was requested.

For authorized changes, verify affected behavior with the smallest sufficient existing checks. Distinguish static checks, local component tests, actual request/persistence behavior and cross-runtime integration; name unverified boundaries. Report files/symbols and source revision rather than unsupported generic architecture findings.

When the affected render, event or Host/custom-element behavior needs real-browser evidence, choose an available browser capability that can exercise that behavior and inspect DOM, console and relevant network activity. Reuse the project's runner when sufficient, and choose CLI or MCP according to interaction and persistent-state needs. Follow the selected tool's own instructions, record the route/Host, initial state, actions and expected versus actual result, and close only sessions created for this task.

For a measured performance gap, capture an authorized trace and compare the same route and state. For unclear cross-file ownership or references, use available symbol-aware retrieval when its language/project support is verified; ordinary search remains sufficient for simple local edits.
