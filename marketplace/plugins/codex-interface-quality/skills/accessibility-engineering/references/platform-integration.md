# Platform integration

Read for semantics, form errors, keyboard/focus, dialogs or native/game integration. Detect actual framework, component library, runtime support and ownership before choosing an implementation.

## Web semantics and names

Use suitable native elements: a button performs an action, a link navigates, and a label names its form control. Inspect the rendered accessibility tree when source composition makes relationships unclear. A visual heading style is not a heading level. Repeated controls need names that distinguish their purpose in context.

ARIA roles are promises of supported behavior, not keyboard implementations. Prefer native semantics, add necessary states/relationships, and preserve the correct roles exposed by compatible components. Do not hide focusable content with `aria-hidden`, apply positive `tabindex` to repair structural order, or name a control differently from its visible label without a justified requirement.

For an already-validated error state, an illustrative native fragment is:

```html
<label for="account-email">Email</label>
<input id="account-email" type="email"
       aria-invalid="true" aria-describedby="email-hint email-error">
<p id="email-hint">Use the address associated with your account</p>
<p id="email-error">Enter a valid email address</p>
```

In a real component, follow its value/validation owner: add error semantics only for the applicable state, keep referenced IDs unique and remove stale relationships when errors clear. This fragment provides relationships, not validation logic or a complete announcement strategy. Preserve authorized UI wording and existing component APIs.

## Keyboard, focus and dialogs

Verify the expected key model for the actual widget, not a universal shortcut list. Tab moves among relevant stops; composite controls can require arrow keys and roving focus according to their pattern. Native controls already implement many behaviors.

For a modal dialog, verify initial focus, a meaningful name, modal interaction, keyboard containment, closing and focus return to a sensible surviving element. Choose initial focus for the content/task; a complex dialog may start at a static heading, while a destructive action should not automatically receive the risky default. Use the installed library's supported behavior or a compatible native dialog, then inspect its actual output. `aria-modal="true"` alone neither contains focus nor blocks background interaction.

Respect asynchronous close/loading states, nested overlays and unsaved-data rules. Do not force Escape to discard work or patch global event handlers for one dialog. If the shared component owner is outside scope, report the dependency and complete allowed local evidence without modifying it.

## Framework and platform routes

| Detected environment | Inspect and preserve |
|---|---|
| Angular | Rendered template bindings, form states, conditional content, library/CDK focus facilities and actual versions. Keep Host/custom-element ownership and event contracts |
| React | Native element output, labels/IDs across SSR and composition, refs, conditional rendering and focus after state updates. Do not assume a particular library or new Hook API |
| Vue | Attribute/slot forwarding, native output, form state and focus after reactive updates. Follow the installed library and supported lifecycle behavior |
| Web async/SSR | Live/status message timing, duplicate announcements, stable IDs, hydration and focus preservation. A hidden alert is not proof it was announced |
| Apple/native | Platform accessibility names, traits, actions, text scaling and assistive-technology support, tested on the actual target. Web DOM/ARIA checks do not prove native behavior |
| Android/native/game | Platform/engine accessibility APIs, input alternatives, text scaling, captions, motion and device/controller support as applicable. Detect package/engine versions and consult their primary guidance |

Use WCAG2ICT as applicable guidance for non-web software, not as proof that a web scanner certifies an app or game. Apple HIG and Google platform guidance inform their target interfaces; the actual requirement and standard govern acceptance.

## Primary references

- [WCAG 2.2](https://www.w3.org/TR/WCAG22/): normative criteria, applicability and conformance
- [WAI-ARIA APG read me first](https://www.w3.org/WAI/ARIA/apg/practices/read-me-first/): native semantics and ARIA behavior commitments
- [Modal dialog pattern](https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/): naming and keyboard/focus behavior
- [WCAG2ICT](https://www.w3.org/TR/wcag2ict-22/): non-web software guidance
- [Apple accessibility HIG](https://developer.apple.com/design/human-interface-guidelines/accessibility)
- [Android accessibility](https://developer.android.com/guide/topics/ui/accessibility/apps)

Sources checked 2026-10-08. Consult compatible package/platform documentation before changing an API.
