# Design sources and adoption

Read when choosing a design-system rule, accessibility target or resolving conflicting UI guidance. Start with the user outcome, confirmed project decisions, supported environment and adopted conformance requirements. Classify the specific passage rather than treating an entire official site as mandatory.

## Source roles

| Source type | What it establishes | Adoption condition |
|---|---|---|
| Web/accessibility specification | [HTML](https://html.spec.whatwg.org/), [WAI-ARIA 1.2](https://www.w3.org/TR/wai-aria-1.2/) platform/role semantics and [WCAG 2.2](https://www.w3.org/TR/WCAG22/) conformance criteria | Identify the normative requirement, applicable platform/version and adopted conformance scope; distinguish informative notes/examples. |
| Pattern/explanation | [APG patterns](https://www.w3.org/WAI/ARIA/apg/patterns/), [WCAG Quick Reference](https://www.w3.org/WAI/WCAG22/quickref/), Understanding documents and [MDN](https://developer.mozilla.org/en-US/docs/Web/API/Popover_API) implementation/compatibility guidance | Use the selected widget pattern and relevant explanation, tracing compliance claims to the specification and exercised evidence. |
| Design system/platform guidance | Component usage, appearance, tokens and platform conventions | Confirm the selected product/system, component version and use case; local sizing or nesting recommendations remain scoped to that system. |
| UX research/method | [NN/g heuristics](https://www.nngroup.com/articles/ten-usability-heuristics/), research findings and usability methods | Use findings to form an observable task hypothesis, retaining population/context and method; distinguish heuristic review, prototype feedback and user testing. |
| Project specification/implementation/acceptance | Confirmed requirements, actual API/pin and exercised behavior | Reconcile decisions with current source and tested state; keep implementation, historical results and current conformance evidence separate. |

Record the relevant source/section, evidence type, version/platform, checked date, adopted decision and reason when they affect the work. For conflicts, compare the actual requirement and guidance, user impact and supported alternatives. Preserve confirmed decisions, surface an incompatible requirement and resolve only dependent work; recency or an official logo alone does not select the winner.

[APG's introduction](https://www.w3.org/WAI/ARIA/apg/about/introduction/) identifies APG as informative guidance, with normative requirements defined by ARIA/WCAG. Its keyboard conventions still inform usable patterns; a deviation needs a supported behavior and applicable standards checks rather than dismissing the guidance or labelling every APG example mandatory.

## Design-system discovery

Use the selected system's relevant component page, not a mandatory multi-site survey. These are discovery entry points; inspect the applicable page/version before adopting its details.

| System | Official entry |
|---|---|
| Material Design 3 | [Material 3](https://m3.material.io/) |
| Apple platform guidance | [Human Interface Guidelines](https://developer.apple.com/design/human-interface-guidelines/) |
| Fluent 2 | [Fluent 2](https://fluent2.microsoft.design/) |
| Carbon | [Carbon](https://www.carbondesignsystem.com/) |
| Atlassian | [Atlassian Design](https://atlassian.design/) |
| GOV.UK | [GOV.UK Design System](https://design-system.service.gov.uk/) |
| USWDS | [U.S. Web Design System](https://designsystem.digital.gov/) |

Names vary across systems. [Fluent Tooltip](https://fluent2.microsoft.design/components/web/react/core/tooltip/usage/) separates supplemental plain text from [Popover](https://fluent2.microsoft.design/components/web/react/core/popover/usage/) structured/interactive content. [Carbon Popover](https://www.carbondesignsystem.com/building-blocks/core/components/popover/guidelines) also supplies a base layer for tooltips and menus, with Carbon-specific size/nesting guidance. [Atlassian Popper](https://atlassian.design/components/popper/usage) is a positioning wrapper rather than a UI widget. Compare purpose and behavior before mapping names or options between libraries.

## Units and conformance scope

| Adopted WCAG criterion | Target-size rule |
|---|---|
| [2.5.8, AA](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html) | At least 24 x 24 CSS px, or its applicable spacing, equivalent, inline, user-agent-control or essential exception. |
| [2.5.5, AAA](https://www.w3.org/WAI/WCAG22/Understanding/target-size-enhanced.html) | At least 44 x 44 CSS px, or its applicable equivalent, inline, user-agent-control or essential exception. |

Check the selected criterion and its exception conditions against actual target geometry. Platform points, project font sizes, visual icon dimensions and CSS pointer target dimensions have different meanings; retain their units and scope. A project's larger target preference can remain a product decision without becoming a universal Web minimum.

Fluent Tooltip/Popover, Carbon Popover, Atlassian Popper, APG introduction/Menu and WCAG target-size guidance checked 2026-10-11, Asia/Taipei. The design-system table provides discovery entries; refresh the applicable component passage when adopting a new platform/version or encountering a conflict. For component terminology and specification fields, read [component patterns](component-patterns.md).
