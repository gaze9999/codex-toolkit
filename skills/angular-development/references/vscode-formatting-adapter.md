# VS Code formatting adapter

Read only for VS Code provider/configuration diagnosis or an explicit editor-output comparison. The [standalone TypeScript method](typescript-formatting.md) does not require these editor steps.

- Identify the current language/resource, effective `editor.defaultFormatter`, extension/provider and actual parser/runtime version used by that provider, including TypeScript when applicable. Installed extensions or saved defaults alone do not establish which provider handled a file.
- Language-specific settings override non-language-specific settings even when the latter have a narrower scope. A language-specific User formatter can override an unscoped Workspace formatter; do not model precedence as workspace always winning. Compare the applicable User, Workspace, folder and language settings for the specific resource.
- Keep TypeScript formatting settings separate from Prettier configuration. Inspect only relevant settings; do not export the whole user configuration, credentials or unrelated values. Map supported options to the selected provider and retain unresolved differences.
- `formatOnSave`, indentation detection, trailing/final whitespace handling, `codeActionsOnSave`, ESLint fixes, organize/sort imports and member-sorting extensions are editor or provider actions, not implicit language-service formatting. Resolve each action's actual implementation before reproducing it outside the editor.
- To claim matching output, compare a bounded synthetic sample under the same TypeScript version, effective formatting options and explicitly selected actions. Report unexecuted actions separately; do not launch an editor or change its settings merely to format source outside it.

## HTML and stylesheet providers

Resolve the file's actual language mode first: HTML/Angular templates, CSS, SCSS
and indented Sass are distinct inputs. Inspect applicable User, Workspace, folder
and language-specific formatter settings, provider/extension versions, project
formatter configuration and parser selection. A saved default establishes the
configured provider, not an observed editor invocation. Keep machine and project
settings local; portable guidance records the discovery method.

Inspect relevant indentation/tab settings and indentation detection separately
from the provider's wrapping and whitespace options. For HTML, check attribute
wrapping, line width, unformatted tags/content and Angular parser support. For
stylesheets, check the selected language's provider and supported parser rather
than inheriting an HTML, CSS or TypeScript choice by filename resemblance. Map
only options the selected provider actually supports. Reproduce a bounded sample
and inspect the scoped diff before applying to authorized files; do not mass-format
unrelated code or silently substitute another formatter.

SCSS uses braces and semicolons; indented Sass uses indentation and newlines as
syntax. Never compare indented Sass by stripping whitespace. Preserve stylesheet
rule and declaration order, cascade behavior, selectors and combinators, custom
property token content, strings, interpolation, comments and syntax-sensitive
spacing. Formatting does not authorize sorting declarations, merging selectors,
changing nesting or deleting comments.

Report formatter execution/idempotence, syntax parsing, compiled CSS comparison
and rendered acceptance separately. Use the project's existing compatible Sass
compiler and equivalent inputs/options when comparing compiled output; preserve
imports, variables, output mode and relevant source-map differences. Compare CSS
semantics without erasing selector or value whitespace. A clean formatter or parser
result does not prove unchanged compiled CSS or rendered layout. Keep unavailable
compiler/browser checks in the existing work record with their concrete effect.
