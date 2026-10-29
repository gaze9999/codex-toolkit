# VS Code formatting adapter

Read only for VS Code provider/configuration diagnosis or an explicit editor-output comparison. The [standalone TypeScript method](typescript-formatting.md) does not require these editor steps.

- Identify the current language/resource, effective `editor.defaultFormatter`, extension/provider and actual TypeScript version used by that provider. Installed extensions or saved defaults alone do not establish which provider handled a file.
- Language-specific settings override non-language-specific settings even when the latter have a narrower scope. A language-specific User formatter can override an unscoped Workspace formatter; do not model precedence as workspace always winning. Compare the applicable User, Workspace, folder and language settings for the specific resource.
- Keep TypeScript formatting settings separate from Prettier configuration. Inspect only relevant settings; do not export the whole user configuration, credentials or unrelated values. Map supported options to the selected provider and retain unresolved differences.
- `formatOnSave`, indentation detection, trailing/final whitespace handling, `codeActionsOnSave`, ESLint fixes, organize/sort imports and member-sorting extensions are editor or provider actions, not implicit language-service formatting. Resolve each action's actual implementation before reproducing it outside the editor.
- To claim matching output, compare a bounded synthetic sample under the same TypeScript version, effective formatting options and explicitly selected actions. Report unexecuted actions separately; do not launch an editor or change its settings merely to format source outside it.
