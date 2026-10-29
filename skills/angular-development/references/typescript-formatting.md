# TypeScript formatting without an editor

Read when the selected formatter is TypeScript and the task runs outside an editor. This is a formatting method, not a provider-selection rule. Use the explicit user-selected baseline or applicable project conventions; report conflicting configuration rather than silently switching to Prettier.

## Inputs and execution

1. Resolve the existing `typescript` package from the target project's manifest/module resolution and record `ts.version`. Do not depend on an editor installation or install a different compiler to format files.
2. Select the reviewed file set and explicit `FormatCodeSettings`. Start with that version's `ts.getDefaultFormatCodeSettings(newLine)` only when its defaults are the agreed baseline, then apply the confirmed options. Record defaults and overrides separately. Preserve each file's newline convention unless changing it is authorized.
3. Use `getFormattingEditsForDocument`, apply text changes from the highest offset downward (reverse original order for equal offsets) and dispose the service. Preview the diff before authorized writes, preserve concurrent changes and skip identical output.
4. Check syntax, idempotence and changed tokens/literals. Formatting does not reorder declarations, normalize access modifiers, rewrite equivalent syntax, organize imports or perform lint fixes. Run those separately only when authorized, with their own evidence.

This pure example takes the existing TypeScript module and resolved options as inputs. It returns text and never writes files, loads editor settings or runs save actions:

```js
function formatText(ts, fileName, source, options) {
  const host = {
    getCompilationSettings: () => ({}),
    getScriptFileNames: () => [fileName],
    getScriptVersion: () => '0',
    getScriptSnapshot: name => name === fileName
      ? ts.ScriptSnapshot.fromString(source)
      : undefined,
    getCurrentDirectory: () => '.',
    getDefaultLibFileName: settings => ts.getDefaultLibFilePath(settings),
    fileExists: name => name === fileName,
    readFile: name => name === fileName ? source : undefined,
  };
  const service = ts.createLanguageService(host);
  try {
    const edits = service.getFormattingEditsForDocument(fileName, options);
    return edits.map((edit, index) => ({ edit, index }))
      .sort((a, b) => b.edit.span.start - a.edit.span.start || b.index - a.index)
      .reduce((text, { edit }) => text.slice(0, edit.span.start) + edit.newText
        + text.slice(edit.span.start + edit.span.length), source);
  } finally {
    service.dispose();
  }
}
```

Use a filename with the actual language extension, including `.tsx` when applicable. This minimal host is for document formatting, not project type checking. Validate the API against the installed package's `typescript.d.ts`; relevant interfaces are `LanguageService`, `FormatCodeSettings`, `EditorSettings` and `SemicolonPreference`.

## Evidence boundary

Record package version, options, selected files, diff and checks. A standalone result is not proof of byte-identical editor output unless the editor's actual TypeScript version and effective options are matched and compared. Prettier options do not become TypeScript options by copying names. ESLint, import organization, member sorting and whitespace/save actions remain separate operations.

Only when an editor comparison or settings diagnosis is requested, read the [VS Code adapter](vscode-formatting-adapter.md). No editor process is required for this method.
