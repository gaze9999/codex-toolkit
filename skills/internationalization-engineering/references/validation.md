# Internationalization validation

Read when selecting checks for changed resources, locale switching, formatting, layout or delivery evidence. Use existing project tools and expand only around affected contracts or unresolved risk.

## Smallest useful matrix

| Changed contract | Focused evidence | Expand when affected |
|---|---|---|
| Resource/message | Parse resources, changed required keys, duplicate IDs and parameter names/types; compile the installed message syntax | Required locale parity, malformed ICU/select branches or extraction/merge output |
| Count/selection | Boundary values such as 0, 1, 2 and a relevant fractional/negative value where permitted, with target-language categories | Additional product-supported locales with different rules |
| Number/date/currency | Explicit locale, time zone, currency and known values, preserving canonical data | Midnight/DST boundaries, precision, date-only input or server/client differences |
| Locale switching | Load success/failure, intended fallback, persisted preference and visible rerender | Rapid changes, stale async responses, navigation, unsaved forms and request isolation |
| Layout/direction | One affected rendered flow with representative long text and correct language/direction | Supported RTL, zoom, narrow viewports, font fallback or mixed-direction content |
| SSR/cache | Matching initial locale/messages/time zone and request/cache identity | Hydration, concurrent users and route/preference precedence |

Select actual product locales, not every language by default. A practical bounded case is a changed cart count in two supported locales, including empty/single/multiple states, followed by one real switch with an unsaved form. Add an unsupported locale only if fallback handling changed.

Resource checks should understand the installed schema and message parser. Do not claim reliable validation from a regex over ICU syntax or add a new generic validator when the build already compiles messages. Missing-key detection must distinguish optional, inherited and intentionally fallback resources.

## Rendered acceptance

Check labels, placeholders, validation errors, loading/empty states, date/number display, links and accessible names in the affected route. Use pseudo-localization only through an available project mechanism; it detects layout/resource gaps but does not establish translation quality. Verify truncation and wrapping in context rather than fixing every long label with a tooltip.

If direction changed, inspect reading order, focus order, logical spacing and mixed-direction identifiers. For dynamic locale changes, verify `lang`/`dir` and localized announcements through the existing owner. Use accessibility-engineering when these semantics change and ui-ux-design for requirement comparison and the actual flow. Do not add unsupported RTL behavior merely to complete a checklist.

Review language and terminology separately using available proofreading and human/context review. Protect specification-defined strings and quotations. Translation services or external evaluators require permission for the actual source strings, context and derived summaries.

## Evidence and unresolved states

Record affected message IDs/locales, checked source state, formatter inputs and environment, route/actions and expected versus observed results. Separate resource parsing, build, formatter tests, browser/native execution and wording review. A build or one locale passing cannot prove all supported locales, SSR or live preference persistence.

If the application or target device cannot run, continue independent resource/type checks and identify exactly which switching, layout, accessibility or native behavior remains unverified. Avoid broad tests solely to make the report look complete.

## Primary references

- [W3C internationalization quick tips](https://www.w3.org/International/quicktips/)
- [Unicode ICU message rules](https://unicode-org.github.io/icu/userguide/format_parse/messages/)
- [Angular internationalization](https://angular.dev/guide/i18n)

Sources checked 2026-10-08. These guide check selection; project acceptance and supported locales determine the required coverage.
