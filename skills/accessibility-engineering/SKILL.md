---
name: accessibility-engineering
description: Implement, diagnose or review accessibility (a11y), UI semantics, accessible names, keyboard operation, focus, errors and assistive-technology behavior. Use for programming changes or accessibility checks in the detected web/native stack, not generic visual redesign or a conformance claim based only on an automatic scan.
metadata:
  version: "0.1.0"
  author: "gaze9999"
  repository: "https://github.com/gaze9999/codex-toolkit"
---

# Accessibility Engineering

Inspect the affected flow, framework/runtime, component library, rendered semantics and actual acceptance requirement. Use the project's applicable standard and target platform; for web work, consult the relevant WCAG criteria and WAI-ARIA Authoring Practices. Preserve source-defined copy, shared-component ownership and useful existing interactions.

## Implement the affected behavior

- Prefer suitable native controls and semantics. Provide meaningful accessible names, labels, roles, states and relationships. ARIA does not create keyboard behavior; avoid redundant or conflicting roles and do not use it to cover an unsuitable element.
- Keep all affected actions keyboard-operable with logical focus order and visible focus. Handle overlays, dialog entry/containment/exit and focus return through the existing compatible pattern, preserving Escape and data-loss requirements.
- Associate instructions and errors with their controls. Expose relevant loading, validation and status updates without duplicate announcements, unexpected focus changes or losing entered data. Do not invent announcements without observing the flow.
- Check affected contrast, non-color cues, zoom/reflow, target sizing and reduced-motion behavior against the applicable criteria, including their conditions and exceptions. A visually plausible screenshot does not prove accessibility.

## Load only the relevant reference

- Web semantics, forms/dialogs, framework integration or native/game boundaries: [platform integration](references/platform-integration.md)
- Automated checks, keyboard, assistive technology or acceptance evidence: [validation](references/validation.md)

Use available Angular, React or Vue development Skills for component/state contracts and ui-ux-design for the representative rendered flow. Use internationalization-engineering when language/direction or localized accessible names change. Missing companion Skills do not remove the required behavior checks.

## Verify and deliver

Begin with the changed markup/state and the smallest useful flow using existing checks. Combine an available scoped automatic scan with actual keyboard operation and relevant assistive-technology checks. Read the validation reference for evidence selection. Install tools or contact external services only within authorization; keep private pages, logs and session material in the approved environment.

Report changed files, actual routes/states, expected versus observed behavior, checked platform/tool versions and unresolved findings. Distinguish source checks, scans, keyboard and assistive-technology evidence. A clean scan or local fix does not establish whole-application WCAG conformance or native support.
