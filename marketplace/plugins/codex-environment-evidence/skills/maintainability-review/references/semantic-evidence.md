# Semantic evidence

Use this after the scan returns `unused` or `needs_review` candidates and a language-server entry covers the same workspace. The scan stays syntax-level; a reference query supplies evidence about resolved consumers within the loaded project scope.

## Select

- Check the candidates the review will act on: proposed removals first, then `needs_review` items with a `symbol`. Keep one review to roughly 40 queries; narrow by path or `checks` and say which candidates stay unchecked.
- The `code_health` result lists the first 40 unused candidates under `candidates` and the first 40 positioned review items under `review`; the rest are in `report.json`.
- `export:` and `member:` candidates carry `line` and `column` at the declared name, both 1-based with columns in UTF-16 units. `file:` candidates have no symbol position; judge them from the result of their exports and the module graph.

## Query

If a local semantic adapter can consume the code-health JSON report and emit `code-health-evidence/v2`, pass the matching workspace and selected candidate IDs. Use the report's `source_files` with the evidence and regenerate it when the merge rejects a changed source. Keep zero-reference results unconfirmed until the relevant graph and entry points have been checked.

Send the candidates in one call where the entry offers a batch tool: `lsp_find_references_batch` on `code_intelligence` takes up to 50 `queries`, each with the absolute `file_path`, `line`, `column` and the candidate ID as `id`, plus `include_declaration: false`. Otherwise call `lsp_find_references` once per candidate. Each result holds `context` (`workspace`, `adapter`, `version`, `provider`, `coverage`), `references` and `total_count`. Send again any position whose error reports the batch time budget; a path outside the configured workspaces returns an error.

A language server answers for the projects it has loaded. In a multi-project workspace (Nx applications and libraries with separate tsconfig files, project references, micro-frontends), consumers in another project can be missing. `code_intelligence` opens the files that mention the symbol before it queries and reports the outcome in `context.coverage.expansion`; `complete: true` means the bounded text search opened every matching file it selected. It does not prove that aliases, re-exports, framework discovery, reflection or external consumers were covered. Verify the maintained entry points and project graph before treating a zero-reference result as confirmation.

| Result | `status` | Record |
| --- | --- | --- |
| `total_count` 0, expansion complete, and the relevant project graph and entry points independently verified | `confirmed` | `references: 0`, exact reviewed scope and remaining external-consumer limits |
| References only inside the declaring file, for an `export:` candidate, and the relevant project graph and entry points independently verified | `confirmed` | count and `note` that the symbol is used locally and only the export is unused |
| A reference in another file, or any reference for a `member:` candidate | `refuted` | count and up to 50 `locations` |
| Zero references with incomplete, absent or unverified project coverage | `unsupported` | Identify the missing scope and follow the steps below |
| Capability or file type unavailable | `unsupported` | `note` with the reason |
| Request timed out, or diagnostics still pending for a project the server has not indexed | `timeout` | |
| Tool error | `error` | `note` with the message |

When expansion is incomplete (`stopped`, `failed` entries, more `matching_files` than `expand_limit`, or `expanded: false`), or the entry reports no expansion:

- Query again with a larger `expand_limit` (up to 100) when the count of matching files exceeds it.
- Otherwise search the whole workspace root for the symbol name in source and template files, outside the declaring file. No other occurrence alone does not confirm removal: record `unsupported` with the unresolved project coverage, unless independent source and project-graph evidence closes that gap.
- An occurrence exists that the query did not return: query that position, or inspect the import, and record `refuted` when it resolves to the candidate. Record `unsupported` with the note `consumer project not loaded` when it cannot be resolved.

## Merge

Build one evidence object and pass it to the scan again with the same root, entries, checks and retention inputs: the `evidence` argument of `code_health`, or `--evidence FILE` on the CLI.

```json
{
  "schema": "code-health-evidence/v1",
  "root": "/absolute/scan/root",
  "items": [
    { "id": "export:src/lib.ts#spare", "status": "confirmed", "provider": "typescript", "provider_version": "5.9.2", "coverage": "project", "references": 0 },
    { "id": "member:src/a.component.ts#AComponent.save", "status": "refuted", "provider": "angular", "references": 1,
      "locations": [{ "path": "src/a.component.html", "line": 12 }] }
  ]
}
```

Copy `id` values from the scan unchanged. Take `provider` from `context.adapter` and `provider_version` from `context.version` when it is present. `coverage` is a short string: `workspace` when `expansion.complete` is `true`, otherwise the value named in the table or `loaded projects`. The merged report adds `semantic` to each matched candidate and a summary with counts per status, `unchecked` candidates and `unmatched` evidence IDs. Treat any `unmatched` ID as stale evidence and query that candidate again.

## Use in the review

- `confirmed` supports a removal proposal together with the checks for registration, reflection, templates and consumers outside the workspace, which a language server does not see.
- `refuted` removes the candidate from removal proposals; cite the first location.
- `unsupported`, `timeout`, `error` and unchecked candidates remain needs-decision cases in the review table.
