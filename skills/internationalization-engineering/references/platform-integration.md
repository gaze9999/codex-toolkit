# Platform integration

Read for resource/schema changes, framework integration, formatting, SSR or native/game localization. Inspect the project's installed versions and actual call chain first; these sources describe options, not a migration requirement.

## Resources and message contracts

Keep the established ID convention and grouping. A resource key should retain its meaning across locales; do not rename or reuse IDs during unrelated maintenance. Record message meaning/context when translators need it. Validate each supported locale against required keys and named parameters, allowing only documented omissions/fallbacks.

Use complete messages with the project's supported message syntax. For an ICU-compatible engine, an English resource might contain:

```json
{
  "cart.items": "{count, plural, =0 {Your cart is empty} one {# item} other {# items}}",
  "profile.greeting": "Welcome, {name}"
}
```

ICU categories depend on the target language and number semantics. Preserve required arguments and `other` branches; do not mechanically copy English categories into every locale or assume plain JSON interprets ICU syntax. Supply translator context for select values and rich text. Use existing safe rendering, not HTML injection to support translated markup.

Fallback is a product behavior: confirm locale normalization, supported regional/script variants, fallback order, missing-key handling and loading failures. Distinguish an intentional fallback from a missing translation. Avoid persistent diagnostics containing private strings or user data.

## Display boundaries

Use Unicode-capable encoding and BCP 47 locale identifiers supported by the actual runtime. Language, region, time zone and currency are separate inputs. An explicit display formatter for an instant could be:

```js
const locale = 'zh-TW';
const timeZone = 'Asia/Taipei';
const instant = new Date('2026-10-08T00:30:00Z');
const displayed = new Intl.DateTimeFormat(locale, {
  timeZone,
  year: 'numeric', month: '2-digit', day: '2-digit',
  hour: '2-digit', minute: '2-digit', hourCycle: 'h23'
}).format(instant);
```

This example formats an instant, not a date-only business value. Detect actual API types before parsing; do not silently shift date-only values through UTC or use locale formatting to parse input. Check target/lib, browser or server support, locale data and option availability. Preserve decimal precision and currency identity; do not select currency solely from UI language. Output punctuation/digits can vary across supported ICU versions, so assert the intended semantic contract rather than accidental punctuation where appropriate.

## Framework and platform routes

| Detected environment | Inspect and preserve |
|---|---|
| Angular | Existing template `i18n`/attribute markers, `$localize` or installed library, extraction/merge/build configuration, locale data and formatter inputs. Use version-matched documentation; do not substitute current APIs into an older Host |
| React | Actual message/provider library, resource loading, hook/context ownership and router integration. React alone does not imply Next.js or a translation provider |
| Vue | Actual Vue/plugin versions, resource scope, interpolation, fallback and reactive locale owner. Vue I18n guidance applies only when that package is present |
| SSR/framework | Request-scoped locale and messages, route/cookie/header precedence, matching first server/client output and cache variation. Do not share mutable locale state across users |
| Native/game | Installed engine/framework localization package, string tables, asset/font coverage, text shaping, layout direction and build targets. Keep serialized IDs, saves and gameplay rules stable; JS `Intl` is not a universal platform API |

Apply `lang` and `dir` through the correct document/component owner. Prefer logical layout properties where compatible and in scope. Mirror directional navigation when required, not every logo, number, media item or technical identifier.

## Primary references

- [W3C internationalization quick tips](https://www.w3.org/International/quicktips/): encoding, language, direction and local conventions
- [Unicode ICU messages](https://unicode-org.github.io/icu/userguide/format_parse/messages/): message arguments and plural/select rules
- [ECMA-402](https://tc39.es/ecma402/): JavaScript internationalization API; verify deployed runtime support
- [Angular preparation](https://angular.dev/guide/i18n/prepare) and [locale formatting](https://angular.dev/guide/i18n/format-data-locale)
- [Next.js internationalization](https://nextjs.org/docs/app/guides/internationalization), only for detected compatible Next.js
- [Vue I18n fallback](https://vue-i18n.intlify.dev/guide/essentials/fallback), only for the installed compatible package

Sources checked 2026-10-08. Recheck version-specific APIs before applying an example.
