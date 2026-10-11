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

## Visible entry points, records and drag interactions

Read for controls inside collapsed/hidden containers, paginated data or reorderable content. Reach the control through the same visible entry and disclosure/navigation sequence as a user. A direct event dispatch or forced action may help diagnosis, but does not establish normal pointer/keyboard operability; retest through the user path.

For a filtered, sorted or paginated view, derive expected stable record IDs from the fixture/source and the active filter, sort, page and page-size rules. Compare displayed records and counts with that expected subset rather than a fixed row count or the full source before filtering/pagination. Exercise changing these controls and opening a detail when their behavior is affected.

For dragging, select the affected transitions: complete a move, cancel it, lose pointer capture, click without dragging, then perform an ordinary action. Check that transient drag state/listeners are released, the intended record is moved, and the selected persistence policy survives reload. Where refresh/reordering must retain a mounted node's identity, verify that node and its focus/selection survive rather than merely matching its text.

[Playwright actionability](https://playwright.dev/docs/actionability) documents the checks bypassed by forced actions. The record and drag cases are engineering acceptance choices, selected by the affected behavior.

## Floating interfaces

Read when changing Tooltip, Menu, non-modal panels/dialogs or modal dialogs. Establish the selected widget pattern, then inspect three independent concerns: semantics and accessible relationships, opening/closing and focus behavior, and positioning/layering. A name such as Popup does not determine a widget role. Share compatible positioning/lifecycle code while preserving each widget's interaction contract and existing component ownership.

Native Popover API content is non-modal and uses the Top Layer; that rendering mechanism does not supply every Menu, Tooltip or Dialog behavior. `showModal()` provides modal behavior and makes the rest of its containing document inert. Match roles, names, trigger relationships and modality to the actual pattern and supported implementation.

Select relevant browser cases from the changed behavior:

| Concern | Observable acceptance |
|---|---|
| Tooltip/help | Pointer and keyboard entry expose the intended description without moving focus into a tooltip. Where WCAG hover/focus criteria apply, content remains readable when the pointer enters it and follows the applicable dismissal/persistence conditions. Interactive content uses its appropriate panel/widget pattern. |
| Focus and keyboard | Initial focus respects the documented autofocus/content policy and usable targets. Menu arrow navigation, Tab/Shift+Tab exit and Escape follow its selected pattern; modal tab containment and focus return follow the dialog workflow. Hidden, removed and disabled targets are handled by that pattern: the ARIA Menu pattern keeps disabled items focusable but inactive. |
| Nested ownership | A nested Escape affects the intended open layer. Closing a parent modal disposes or closes its owned floating content; focus does not return to a removed, hidden or inert opener. Background interaction matches non-modal versus modal behavior within the relevant document. |
| Position and compatibility | In affected transformed/overflow containers, supported viewport/zoom, scroll and resize states, content remains positioned and readable. Exercise the supported native Top Layer path and the documented DOM fallback when capability handling changes; high z-index alone does not prove clipping is resolved. |
| Cleanup and relationships | Reopen and teardown release owned handlers/DOM and restore existing accessible relationships such as `aria-describedby`, retaining descriptions owned by other components. Trigger states such as `aria-haspopup`/`aria-expanded` agree with the actual role and open state where applicable. |

Sources checked 2026-10-11: [MDN Popover API](https://developer.mozilla.org/en-US/docs/Web/API/Popover_API), [MDN showModal](https://developer.mozilla.org/en-US/docs/Web/API/HTMLDialogElement/showModal), [WAI-ARIA Menu](https://www.w3.org/WAI/ARIA/apg/patterns/menubar/), [WAI-ARIA modal Dialog](https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/) and [WCAG hover/focus content](https://www.w3.org/WAI/WCAG22/Understanding/content-on-hover-or-focus.html). Apply the selected pattern and supported versions; these cases are not a mandatory suite for unrelated UI work.

## Streaming tables and details

Read these cases when data updates can reorder interactive rows or replace open details. Resolve whether the stream carries full state, ordered changes or log entries, then test the project's selected update policy with identifiable fixture records.

| Case | Observable acceptance |
|---|---|
| A row moves between pointer targeting and activation | The opened or modified record has the intended stable ID. A row index or matching label alone cannot identify it. |
| Updates arrive during keyboard focus, selection or editing | Focus, selected record and unsaved input follow the agreed policy. A removed record has an explicit state and never silently retargets an action. |
| Hover/focus protection is selected | Data keeps arriving while presentation is held; pending state stays bounded. Leaving the protected state applies the accepted latest snapshot, preserving sorting and open detail identity. Test pointer and keyboard paths separately. |
| Bursts, duplicates or reconnects change revisions | Accepted state converges to the expected generation/version, required events survive and stale responses cannot replace newer accepted data. |
| A route is hidden, revisited or closed | Hidden-view work follows the subscription policy, re-entry catches up correctly and owned listeners/streams/callbacks are released on teardown. |
| Summary counts exceed displayed detail capacity | Source total, filtered count, retained history and returned/displayed limit have distinct meanings. Validate arithmetic and truncated-detail behavior from fixtures. |

Use observable states and relevant requests to synchronize the check. Prefer the selected browser tool's supported waiting/assertion behavior over arbitrary sleeps. Keep rendered fixture evidence and real source/API evidence identifiable.

For automatically updating content, evaluate applicable [WCAG 2.2.2 pause/stop/hide requirements](https://www.w3.org/WAI/WCAG22/Understanding/pause-stop-hide.html), including its essential-content exception. Focus-only suspension leaves a separate accessibility requirement to assess: the user must be able to pause without holding focus captive. Choose the mechanism within the product's requirements; a refresh button and a presentation-pause control serve different purposes.

Sources checked 2026-10-10: [Playwright assertions](https://playwright.dev/docs/test-assertions) for observable-state waiting, WCAG for pause criteria, and [MDN SSE](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events) for stream lifecycle. The fixture cases above are engineering acceptance choices, selected by the affected behavior.

## Evidence that supports a finding

Use a compact finding with the requirement, observed discrepancy, impact, route/state and reproduction, expected result, evidence, responsible owner and retest status. Link the relevant screenshot or source when it helps verification. Prioritize blocked actions/data loss or wrong information, then interaction/layout failures, then cosmetic discrepancies by actual impact; do not invent severity from file length or preference alone.

For example, a request that refresh preserve an open detail panel needs an observation of refresh while the panel is open and scrolled. Merely finding a retained `selectedId` in source does not prove its scroll/focus survive, and a correctly sized panel can still show the wrong record. After a fix, repeat the same action and compare both visible state and record identity.

Geometric checks, image differences and accessibility scans are supporting signals. Animation, dynamic data and font rendering may explain image differences; matching pixels may still hide an inert control or incorrect values. A finding must identify the user-visible discrepancy and its evidence, with uncertainty retained when the source or expected behavior is unknown.
