# Accessibility validation

Read when selecting checks, reviewing scan findings or reporting accessibility evidence. Start with affected behavior and required acceptance; do not infer complete conformance from a score or one tested screen.

## Smallest useful evidence

| Affected behavior | Initial check | Expand for the unresolved risk |
|---|---|---|
| Labels/roles/states | Changed source plus rendered DOM/accessibility tree, unique IDs and names | Dynamic relationships, component forwarding or assistive-tech interpretation |
| Keyboard/widget | Operate the real entry/action/exit using the expected keys, inspect focus visibility/order | Nested widgets, disabled/loading states, conditional removal or alternate input |
| Dialog/overlay | Open by keyboard, verify initial focus/name, containment, close and return | Background interaction, nested overlays, async close or removed trigger |
| Form/errors/status | Enter/submit invalid and valid data, inspect associations and updates without state loss | Screen-reader announcements, async validation and repeated status changes |
| Visual/motion | Relevant contrast/non-color cues, zoom/reflow, target size and reduced-motion state | Actual viewport/text scale/device combinations required by the changed flow |
| Native/game | Target platform semantics and one real supported assistive/input flow | Additional devices, controllers, text scale or platform APIs changed by the patch |

Select the project's required WCAG level and exact criteria before judging failure. Preserve criterion conditions and exceptions, including component states and content that must retain a two-dimensional layout. Automated tools can help identify contrast or semantics issues, but confirm the actual foreground/background/state and actionable source location.

## Combine compatible checks

Use existing lint, type, component or browser tools first. If an automatic scanner is already available, scope it to the affected served route/state and record rules/version/configuration and excluded regions. For a detected compatible Playwright project, use its existing accessibility integration; the documentation shows one possible axe integration, not permission to install another dependency or subscription.

When the project already uses compatible Storybook accessibility tests, inspect the effective `parameters.a11y.test` at project, component and story scope, plus any disabled or excluded checks. In the current [Storybook workflow](https://storybook.js.org/docs/writing-tests/accessibility-testing), `todo` reports warnings in the local UI without accessibility output or failures in CI, while `error` makes violations fail the test. A green CI result therefore needs the tested mode, actual resolved scanner/browser versions and story/state coverage to establish what was checked. Verify the installed version before relying on this behavior. Source checked 2026-10-21, no project runner or browser behavior was exercised by that documentation check.

Operate the flow with the keyboard independently of the scanner. Confirm focus order/visibility, all affected actions, escape/recovery and preservation of input. A script that merely dispatches a click does not prove keyboard usability. Use supported role/name locators for stable assertions where available, without claiming those assertions reproduce a screen reader.

For changed announcements, accessible names/states or complex focus behavior, use relevant assistive technology on the actual target, such as an available screen reader. Record OS, browser/app and assistive-technology versions, actions, expected and observed output. Avoid universalizing one combination. If that environment is unavailable, preserve the explicit evidence gap while completing independent checks.

One bounded dialog check might cover keyboard open, the accessible name, initial focus, forward/reverse Tab, loading/error updates, close and focus return. Add invalid-form announcements only when that dialog contains or changes those behaviors. Do not turn an unrelated layout edit into a whole-application audit.

## Findings and delivery

Tie each observed finding to the requirement/criterion, affected route/state, reproducible action, source location and actual impact. Keep existing issue IDs stable. Separate automatic findings awaiting confirmation from reproduced defects and fixed/retested behavior. Missing environment access or a scanner subscription is a verification limit, not an application defect.

Report source/type checks, automatic scans, keyboard operation, visual review and assistive-technology checks separately. Keep tool errors and not-run states visible. A clean scan, screenshot or local patch cannot establish whole-site/app WCAG conformance, authorization, production state or unrelated platform support.

## Primary references

- [W3C accessibility evaluation overview](https://www.w3.org/WAI/test-evaluate/): ongoing evaluation and limits of automatic tools
- [WCAG 2.2](https://www.w3.org/TR/WCAG22/)
- [WAI-ARIA Authoring Practices](https://www.w3.org/WAI/ARIA/apg/)
- [Playwright accessibility testing](https://playwright.dev/docs/accessibility-testing), only for a detected compatible runner

Sources checked 2026-10-08. These guide evidence selection; actual acceptance and platform support determine the required checks.
