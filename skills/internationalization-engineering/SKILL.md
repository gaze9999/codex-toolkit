---
name: internationalization-engineering
description: Implement, diagnose or review internationalization (i18n), translation resources, locale switching, plural rules, localized formatting and bidirectional UI in the detected application stack. Use for programming behavior involving multiple languages or regions, not ordinary prose proofreading or translating a document.
metadata:
  version: "0.1.0"
  author: "gaze9999"
  repository: "https://github.com/gaze9999/codex-toolkit"
---

# Internationalization Engineering

Inspect the affected feature, supported locales, runtime/package versions, message resources, locale owner and rendering path. Clarify the requested language/region behavior and preserve source-defined copy, API formats, identifiers and user preferences. A request for one wording correction does not authorize adding an internationalization framework or translating the application.

## Implement the affected contract

- Reuse the actual resource schema, stable message IDs and existing translation mechanism. Keep complete messages with named parameters and supported plural/select rules; do not assemble translated sentences from fragments or treat every language as having singular/plural forms identical to English.
- Separate language, region, time zone and currency. Apply supported locale formatting at display boundaries, preserving transport values, date-only meaning, precision, validation and parsing contracts. A localized display string is not an API value.
- Follow the current locale and preference owner. Preserve lazy-loading, loading/error/fallback behavior, reactive identity, cancellation and unsaved state. SSR and the first client render must agree on locale, time zone and loaded messages.
- Check affected `lang`/`dir`, text expansion, truncation, logical layout and accessible names. Translate authorized user-facing content while preserving technical IDs, quotations and specification-controlled labels.

## Load only the relevant reference

- Resource schema, framework integration, formatting or native/game localization: [platform integration](references/platform-integration.md)
- Missing keys, parameters, plurals, switching, rendering or acceptance evidence: [validation](references/validation.md)

Use available Angular, React or Vue development Skills for their affected component/state contracts. Use accessibility-engineering for changed language/direction semantics, keyboard/focus or announcements, and ui-ux-design for rendered-flow acceptance. Use multilingual-proofreading for wording and terminology; it does not establish resource or runtime correctness. If a companion Skill is unavailable, retain the required checks and state the missing evidence.

## Verify and deliver

Start with changed resources, parameters, fallback and representative formatter/switching checks using existing project tools. Expand to rendered states, long text, RTL or SSR when affected. Read the validation reference for the smallest useful matrix. Do not install packages, change translation providers or send private strings externally without authorization.

Report changed files/locales, actual checks, expected versus observed behavior and unverified runtime states. Resource validation alone does not prove live switching, translation quality or complete locale coverage.
