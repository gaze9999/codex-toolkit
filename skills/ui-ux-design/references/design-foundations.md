# Design foundations and reference selection

Use for new UI, prototypes, design-system choices or unresolved hierarchy, layout and interaction decisions. Load the relevant sections, not every linked manual. Keep [detail acceptance](detail-review.md) as the check of the actual result.

## Apply references in context

When no project design system or platform requirement selects the source, start with Apple HIG, then Google Material. Explicit requirements, confirmed decisions, platform conventions, accessibility requirements and existing components govern implementation. For an established Material application, preserve its coherent behavior and use Apple principles where compatible. Use [design sources](design-sources.md) to distinguish normative standards, patterns, platform guidance and research before adopting a passage.

Select a representative task, user/input mode, platform and viewport before borrowing a pattern. Compare its purpose and constraints with the target. Native pt, Android dp/sp and web CSS px are different units; use the applicable platform guidance and web criteria instead of a universal size rule. Identify the source and reason when recommendations conflict.

## Primary: Apple

Start with [Human Interface Guidelines](https://developer.apple.com/design/human-interface-guidelines), then the affected topic:

- [Layout](https://developer.apple.com/design/human-interface-guidelines/layout): adapt to available window space, retain familiar functionality and keep content/actions clear of obstructing UI. Apply consistent alignment and readable content width to the target platform.
- [Typography](https://developer.apple.com/design/human-interface-guidelines/typography): create a legible hierarchy and test supported text sizes, long labels and localized content. Do not shrink important information simply to fit a layout.
- [Accessibility](https://developer.apple.com/design/human-interface-guidelines/accessibility): provide consistent, perceivable and adaptable interaction; preserve relevant assistive and personalization support.

Choose platform-specific behavior when building for Apple devices. On the web, translate these principles into supported components and browser behavior. Native blur, translucent surfaces, animation, fonts and symbols need a concrete purpose, adequate readability, platform support and permission before adoption.

[Apple Design Resources](https://developer.apple.com/design/resources/) is the official template/UI-kit entry point. Select the target platform and version, inspect the relevant usage terms and use an available compatible design tool. Link to the resource rather than copying proprietary kits, fonts or icons into this Skill.

## Secondary: Google

[Material Design](https://m3.material.io/get-started) organizes foundations, styles and components and links its Material 3 Design Kit. Use it for systematic component states and reusable design decisions where compatible with the project.

The official [Material 3 theming codelab](https://developer.android.com/codelabs/m3-design-theming?hl=en) explains semantic color/type roles and named design tokens. Map decisions to the existing theme owner, retain meaningful foreground/background pairs, and check the target theme and text settings. A token name or generated palette is not contrast proof. Do not add a parallel theme or library solely to resemble Material.

## Key supporting references

| Question | Source | Use |
|---|---|---|
| Can users perceive and operate the web interface? | [W3C WCAG 2.2](https://www.w3.org/TR/WCAG22/) | Select the required conformance level; check contrast, keyboard access, focus, reflow, labels and errors. Standards constrain the result independently of brand preference. |
| How should a complex widget behave? | [WAI ARIA Authoring Practices](https://www.w3.org/WAI/ARIA/apg/) | Reference dialog, tabs, combobox and grid semantics, keyboard operation and focus. Prefer suitable native HTML; distinguish a data table from an interactive grid. These patterns are guidance, not complete conformance proof. |
| Is the interaction understandable and recoverable? | [Nielsen's usability heuristics](https://www.nngroup.com/articles/ten-usability-heuristics/) | Inspect feedback, familiar language, consistency, recognition, error prevention, cancel/undo and recovery. Heuristics identify risks; observed user/task evidence establishes actual outcomes. |
| How can dense data stay usable? | [Carbon data-table guidelines](https://www.carbondesignsystem.com/building-blocks/core/components/data-table/guidelines) | Compare scanning, grouping, filtering, selection, batch actions and expandable details. Keep essential data visible; retain project density and ownership rather than replacing tables with decorative cards. |

For pointer targets, [WCAG 2.2 target-size guidance](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum) includes size, spacing and exceptions. Check the applicable criterion and input context; a fixed size alone does not validate the interaction. Automated scans supplement real keyboard, focus, zoom and task checks.

## Turn a reference into a decision

Record only what changes the implementation or review: task/state, source section, applicable principle, project constraint, chosen adaptation and observable acceptance. A form may borrow hierarchy and recovery guidance; a dense dashboard may borrow table patterns while retaining existing components. Test the real target with representative data, refresh, keyboard and viewport states relevant to that decision. Do not report a retrieved template or an attractive prototype as accepted implementation.

Sources checked 2026-10-08. Apple topic content was read from its official documentation JSON when HTML required JavaScript; Material's overview was partly search-indexed, with the official theming codelab read directly. Recheck relevant platform/version guidance when applying it. This reference links external material and contains no redistributed design kit.
