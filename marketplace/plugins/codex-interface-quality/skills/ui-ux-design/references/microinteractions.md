# Microinteraction design and acceptance

Use for a bounded interaction or meaningful state change: selection, disclosure, copy, refresh, submission, navigation, validation, completion or recovery. Preserve the requested scope and the owning specification's copy and display triggers. A request for ideas returns recommendations; implement only authorized changes.

## Choose the feedback

A microinteraction connects a trigger to understandable feedback and a stable outcome. Animation is optional. Background weather, idle characters and continuous scenery are ambient motion, not evidence that an action worked.

Choose effects for orientation, acknowledgement, progress, correction or recovery. Prioritize understanding and control over decorative polish. Reuse component states and design tokens. Do not add an animation library, sound, haptics, toast or confirmation step solely to make an action feel responsive.

| Part | Required decision |
|---|---|
| Trigger | Exact pointer, keyboard, touch or source-state event; distinguish activation from background updates |
| State owner | Stable record/action ID and authoritative states; idle, pending, success, failure and cancelled where applicable |
| Feedback | Visible or accessible cue and purpose; stable geometry, without relying only on color or motion |
| Completion | Actual API, clipboard, persistence or domain confirmation that permits success |
| Timing | Existing motion tokens or scoped choice; never delay the action or infer completion from a decorative timer |
| Interruption | Repeat activation, reversal, cancellation, navigation, replacement and out-of-order responses |
| Alternatives | Keyboard/focus, touch, reduced motion and necessary nonvisual feedback |
| Lifecycle | Hidden view behavior and the owner that removes timers, listeners and animation resources |

Use [the brief](../assets/microinteraction-brief.md) only when a structured packet helps. Keep small decisions in task context. Save a work record only when requested or required by the owning project; do not create a parallel microinteraction ledger.

## Common patterns

| Pattern | Useful behavior | Failure to prevent |
|---|---|---|
| Hover, focus and press | Distinct states with a stable hit area and activation target | Hover-only meaning, shifting targets, hover becoming persistent selection |
| Linked selection | Preserve the same record across list, detail and visual view; add a non-color cue | Retargeting by row index or recreating entities just to animate them |
| Refresh or submit | Pending feedback where useful, then confirmed completion or actionable failure | Fake timed success, duplicate side effects, controls stuck after an error |
| Copy or export | Confirm the promised output after platform acceptance or production | Success for a rejected clipboard write, empty artifact or wrong capture scope |
| Disclosure or menu | Predictable placement, focus and dismissal during transitions | Clipping, inaccessible hover-only content, delayed focus or dismissal |
| Pagination or navigation | Preserve orientation, content geometry and appropriate focus | Layout jumps, stale responses replacing the selected page, replaying every row animation |
| Live value or threshold | Highlight a confirmed meaningful change once; distinguish stale and unknown data | Repeated alerts for unchanged values or missing data treated as zero |
| Completion or history | Respond once per confirmed domain transition and stable identity | Confusing turn end, request acceptance or retry with completed work |
| Reversal or cancellation | Continue from the current visual state; choose ignore, queue, replace or deduplicate by semantics | Jumping to the initial pose, accumulating queues, assuming cancellation rolled back a write |

Prefer transform/opacity for simple motion when compatible, then verify layout, rasterization and text readability in the actual renderer. Choose duration and easing by purpose and existing tokens; a universal millisecond value is not an acceptance criterion. Do not animate large surfaces solely because it is possible.

## Verify the interaction, not just the CSS

- Exercise the visible entry point and relevant pointer, keyboard or touch alternative. Check focus and hit targets before, during and after transitions.
- Check applicable initial, pending, confirmed, failed and recovered states. Animation completion does not establish operation completion.
- Try rapid repeat activation, reversal, dismissal/reopening, hidden/visible transitions and navigation away where relevant. Verify the chosen concurrency policy and cleanup.
- For streamed data, follow [detail review](detail-review.md#streaming-tables-and-details). Preserve identity and selection; background updates must not replay entrance feedback without a meaningful new event.
- Check reduced motion with equivalent immediate feedback. Do not remove content or disable the action. Use the accessibility skill for semantics and nonvisual output; avoid duplicate announcements for incidental updates.
- Assess pause/stop/hide needs for automatic movement separately from interaction-triggered motion. One media query does not establish complete accessibility.
- Observe intermediate and final states when animation is required. Static screenshots and syntax checks do not establish timing, reversal, responsiveness or cleanup.
- Report exercised states and platforms. Mock success validates that fixture path, not production completion. Reuse existing browser/test tools; do not introduce an MCP or a fixed tool bundle for semantic review.

## Ownership and sources

Main owns scope, state semantics and acceptance. A UX reviewer may inspect an assigned journey. The component/application owns implementation, visual-development owns renderer lifecycle, and accessibility-engineering owns applicable access checks. Role names do not grant mutation, deployment or delegation authority.

Public references checked 2026-11-15:

- [W3C: Animation from Interactions](https://www.w3.org/WAI/WCAG22/Understanding/animation-from-interactions.html): nonessential interaction-triggered motion and user control, Level AAA
- [W3C: Pause, Stop, Hide](https://www.w3.org/WAI/WCAG22/Understanding/pause-stop-hide.html): qualifying automatically moving or updating content
- [MDN: prefers-reduced-motion](https://developer.mozilla.org/en-US/docs/Web/CSS/@media/prefers-reduced-motion): browser signal for reduced motion
- [W3C: Status Messages](https://www.w3.org/WAI/WCAG22/Understanding/status-messages.html): appropriate programmatic status feedback without moving focus

The pattern matrix and test selection are engineering guidance, not a universal design-system specification or a conformance claim.
