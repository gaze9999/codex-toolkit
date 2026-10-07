# UI acceptance and detail review

Use this mode for user-visible changes and requests to find layout defects, incorrect information or results that diverge from the original description. Review-only work returns findings; an existing implementation/fix authorization includes correcting and retesting in-scope defects. A reference example or another conversation's request does not authorize changes to that other application.

## Establish what must match

- Reconcile the original request, later corrections, governing specification and confirmed decisions. Keep still-valid earlier requirements, identify superseded choices and resolve missing decisions only for dependent work. Do not silently replace a requested detail with an easier design or a component default.
- Track observable acceptance in task context: requirement/source, route or section, relevant state, expected behavior, observed evidence and result. Use `pass`, `fail`, `not tested` or `blocked` with a concrete reason. A source-only inference remains unverified in the rendered interface. Do not create a separate report file unless requested.
- Determine the actual served revision, component/library version, locale, supported viewport/input modes and relevant data source. Preserve the project's theme, terminology, density and saved preferences. Historical examples guide what to inspect; their exact pixel sizes, row counts and refresh intervals are not universal defaults.
- Follow existing shared-component ownership. Diagnose whether a defect belongs to data/configuration, application composition, shared implementation or unsupported usage. Fix within the authorized owner; provide a minimal reproduction and required upstream change when another owner is needed. Do not conceal a shared defect with conflicting global CSS or edit another owner's work.

## Observe, diagnose, fix and retest

1. Select representative affected flows and their realistic states. Add long content, narrow layout, loading/empty/error, refresh or locale cases when they exercise the changed behavior. Expand beyond those flows only for a demonstrated dependency or regression.
2. Run or reach the actual target through its established entry point. Operate the page with an available browser tool and its Skill, using fresh UI targets and an owned session. Do not ask for user screenshots when you can inspect the target directly. If unavailable, use supplied screenshots/source evidence and name the missing rendered checks.
3. Inspect the rendered screen, not only DOM text or computed CSS. Capture and view screenshots for geometry, density, clipping, occlusion and comparison with supplied visual references. Record route, state, viewport and locale. If screenshot viewing is unavailable, report that boundary rather than treating a saved image as visually checked.
4. Inspect DOM geometry/semantics, console and relevant requests as needed to explain observed discrepancies. Trace displayed values through the source, transformation, aggregation, formatter and binding. Retain meaningful expected-versus-observed evidence without collecting unrelated/private content.
5. Fix the smallest complete cause within scope, then rerun the failing state and affected adjacent behavior. Verify after data updates, font/layout settling and user interaction where relevant. A matching initial frame can still fail on refresh or long content. Keep unresolved defects explicit instead of repeating ineffective styling changes.
6. Reconcile the acceptance list again before delivery, including earlier requirements. State actual checks, remaining failures and unavailable evidence. Distinguish fixture rendering, real data/API behavior and deployment; a mock source can verify layout without proving production values. Close only owned sessions and temporary processes.

## Inspect the affected detail dimensions

Select relevant rows rather than applying every component or state to every page.

| Dimension | What to compare or exercise |
|---|---|
| Layout and density | Table header/body alignment, tabs/subtabs, heading/filter gaps, card sizing, modal section placement, wrapping, overflow and overlapping records. Preserve essential labels, quantities, costs/effects, states and actions when compacting. |
| Responsive content | Supported viewport and zoom/input modes, long labels/IDs/logs, expanded trees/objects and large numbers. Intended table scrolling is different from page overflow or clipped actions. Check supported locales with different text lengths. |
| Data and description | Actual field identity, source/version, calculation and aggregation, active filters/time range, timestamp/time zone, units and scope. Compare a displayed sample with its source and expected rule. Counts need arithmetic evidence; a screenshot alone cannot prove them. |
| Numbers and status | Preserve meaningful zero, null, unknown, permission failure and not-yet-loaded states. Use rounding/scientific notation when approximation is allowed and keep exact values accessible where needed. Presentation cannot restore precision already lost in a JS Number. Tags represent actual status and retain readable text/contrast. |
| Drill-down and editing | Promised links/counts open the right details, available error/log/input/output content is readable, inline edit remains inline when specified, save/cancel and failed validation preserve intended state. Avoid empty or misleading affordances. |
| Refresh and asynchronous state | Loading-to-data transitions, chart measurement and table updates remain stable. Refresh preserves modal/tab/disclosure state, focus, scroll, selection and unsaved edits according to the spec. User changes are not overwritten by late responses. |
| Filters and navigation | Each control affects its declared data scope, reset/sort/pagination and URL/state behavior agree. Shared time ranges remain shared when specified. Missing-data tabs have a meaningful hide/disable/empty behavior instead of a false success state. |
| Help and language | Headings, labels, units and tooltips explain actual meaning, aggregation and actions concisely. Place numeric units legibly. Preserve original required copy and use the target locale's terminology. Attach help to the relevant control when appropriate, avoid redundant help icons and repeated generic caveats. |
| Keyboard and accessibility | Affected controls have meaningful names, keyboard operation, visible focus and appropriate states. Modal/menu opening, closing and focus return work; labels, errors and help remain discoverable without hover-only use. Preserve readable contrast and supported touch targets. |

## Evidence that supports a finding

Use a compact finding with the requirement, observed discrepancy, impact, route/state and reproduction, expected result, evidence, responsible owner and retest status. Link the relevant screenshot or source when it helps verification. Prioritize blocked actions/data loss or wrong information, then interaction/layout failures, then cosmetic discrepancies by actual impact; do not invent severity from file length or preference alone.

For example, a request that refresh preserve an open detail panel needs an observation of refresh while the panel is open and scrolled. Merely finding a retained `selectedId` in source does not prove its scroll/focus survive, and a correctly sized panel can still show the wrong record. After a fix, repeat the same action and compare both visible state and record identity.

Geometric checks, image differences and accessibility scans are supporting signals. Animation, dynamic data and font rendering may explain image differences; matching pixels may still hide an inert control or incorrect values. A finding must identify the user-visible discrepancy and its evidence, with uncertainty retained when the source or expected behavior is unknown.
