# Component patterns and specifications

Read for ambiguous component terminology, interaction design or component specification/handoff. Identify the user's action and content first. Names below are a vocabulary for selecting behavior, not a component implementation checklist.

## Component glossary

| Term/aliases | Purpose and content | Background, focus and dismissal |
|---|---|---|
| Popup | General term for content appearing over or beside another region | Determine the underlying widget, modality and input policy; the name supplies no ARIA role. |
| Tooltip | Brief supplemental text, without interactive controls | Keep focus on the trigger; expose help on keyboard focus as well as hover and support applicable hover/focus dismissal and persistence. Keep essential information/errors available in the main flow. |
| Popover | Contextual details, local settings or structured/interactive actions | Native Popover is non-modal; choose the widget semantics and focus policy separately. Top Layer and light dismissal are rendering/lifecycle mechanisms. |
| Hover Card | Rich contextual preview, sometimes containing links/actions | Provide a keyboard/touch entry and persistent reading path; interactive content needs an appropriate panel/widget pattern rather than tooltip semantics. |
| Menu / Dropdown Menu | A set of commands | Follow the chosen Menu pattern for item focus, arrows, activation, Tab exit and Escape/focus return; preserve inactive but focusable disabled menu items when adopting APG. |
| Listbox / Combobox | Option selection / input with suggestions | Distinguish selection from command activation. Follow the selected pattern's option, active descendant, input focus and popup policy; a visually similar dropdown does not imply `role=menu`. |
| Context Menu | Commands for an identified target/context | Provide an equivalent keyboard entry and preserve target identity; use Menu navigation and return focus to the usable invoking context. |
| Dialog / Modal | A named interaction region / a mode that restricts background interaction | A dialog may be modal or non-modal. Specify initial focus, Tab behavior, Escape/cancel and valid focus return; modal behavior includes actual background restriction. |
| Drawer / Sheet | Side or edge presentation of navigation/details/editing | Select modal or non-modal behavior from the task; placement alone does not define focus containment or background access. |
| Toast / Snackbar | Transient action feedback, optionally with a simple recovery action | Avoid unsolicited focus transfer. Select announcement urgency/lifetime and readable history/recovery when needed; blocking errors need a persistent actionable state. |
| Alert | Important dynamically announced information | Choose urgency from the event, not the word error. An alert does not move focus; interactive acknowledgment uses its appropriate dialog/other pattern. |
| Lightbox | Enlarged media/viewer surface | Define viewer controls, modality, dismissal and focus return; a backdrop alone does not provide modal semantics. |
| Disclosure / Accordion | In-flow expansion / related expandable sections | Keep ordinary document flow and labelled toggle state. Preserve the selected independent/single-open policy and focus on a usable control. |

Use [APG patterns](https://www.w3.org/WAI/ARIA/apg/patterns/) and the applicable [WAI-ARIA definitions](https://www.w3.org/TR/wai-aria-1.2/) for the selected widget. For Menu, [APG](https://www.w3.org/WAI/ARIA/apg/patterns/menubar/) keeps disabled items focusable but inactive; ordinary disabled form controls have a different policy. Do not apply one disabled rule across all controls.

Separate three concerns: meaning/accessible relationships, opening/closing/focus, and positioning/Portal/Top Layer. Share compatible lower-level state, positioning and disposal while preserving each pattern's public interface; avoid a universal Popup component that guesses all behavior from its name. [Native Popover](https://developer.mozilla.org/en-US/docs/Web/API/Popover_API) and [modal dialog](https://developer.mozilla.org/en-US/docs/Web/API/HTMLDialogElement/showModal) provide different platform behavior; a popover attribute does not provide a complete Menu or Dialog pattern.

System names/aliases are illustrated in [design sources](design-sources.md#design-system-discovery). Map the selected library's actual export/declaration, options and consumer pin to this vocabulary before using it; proposed APIs and newer local exports remain separate from a consumer's installed capabilities.

## Adaptable component/interaction specification

Use the existing project format. Select fields that explain the changed decision and observable acceptance; a small copy/layout fix need not generate a new specification document.

| Concern | Useful fields |
|---|---|
| Outcome/content | Purpose, use/avoid cases, intended task result, essential information and error placement. |
| Structure/presentation | Anatomy, variants, existing tokens/styles, normal/disabled/loading/empty/error/success/recovery states. |
| Interaction/semantics | Trigger/dismissal, background access, initial focus, Tab/arrows/Escape/return, role/name and relevant ARIA relationships. |
| Placement/layers | Anchor, placement/collision, scrolling/resizing/zoom/overflow, nested owner, native path and supported fallback. |
| Supported use | Responsive layout, locale/text direction, larger text, input modes, reduced motion and adopted accessibility criteria. |
| API/lifecycle | Actual API/version/pin, input validation, supported limits, data/state owner, async/cancel/failure/save and teardown. |
| Acceptance/provenance | Requirement/source and adoption reason, tested revision/dirty artifact identity, route/state/viewport/locale, expected versus observed, `pass` / `fail` / `not tested` / `blocked` and evidence. |

Retain one state owner, stable record/DOM identity where required, raw values separate from display formatters, capability detection, bounded resources and owned cancellation/disposal. Shared components own reusable interaction/lifecycle; consumers own data/API/authorization/persistence/sorting and application pages. Inspect original values before changing displayed precision or status.

## Choose the handoff artifact by the decision

Use a research plan, Persona/JTBD, Journey Map, IA/Sitemap, task flow, wireframe/prototype, component spec, handoff, usability report or accessibility audit only when it answers the task's unresolved question. Heuristic findings and prototype feedback guide hypotheses; usability claims need the relevant observed task/user evidence.

When already present, link matching Figma components/prototypes or Storybook docs/controls/variants. [Autodocs](https://storybook.js.org/docs/writing-docs/autodocs/) and [MDX](https://storybook.js.org/docs/writing-docs/mdx/) are optional documentation mechanisms for compatible projects. Reuse maintained docs, gallery, declarations/API index and browser flows where they exist; selecting a reference does not require a new framework, design file, dependency, font or service.

For implementation acceptance, use [detail review](detail-review.md): normal visible entry, original source through projection/aggregate/formatter/binding, rendered inspection plus relevant DOM/console/network, and affected lifecycle/native/fallback cases. Keep fixture/browser, real device/assistive technology, actual API/account and production/release evidence distinct. Select checks by changed behavior rather than running the whole glossary for every UI edit.

Pattern and platform references checked 2026-10-11, Asia/Taipei. Verify the selected pattern and supported platform/version when implementing.
