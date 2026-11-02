# Output language and direct style

Read when maintaining output-language rules, concise English, Taiwan wording or prose checks across clients and Plugins.

## Choose the audience and surface

| Authored surface | Required handling |
| --- | --- |
| AI instructions, guides, indexes and handoffs | Concise English, with exact source literals retained |
| Human-facing Chinese | Taiwan Traditional Chinese, Taiwan wording and the selected punctuation profile |
| Requested English | Concise, direct English using the document's English convention |
| Progress, final replies, tool questions/options, captions and authored comments | Apply the same audience/language choice before sending |
| Quoted sources, UI/specification copy, code, identifiers and legal notices | Preserve exact protected text and check surrounding authored prose |

Write the result, action and necessary condition directly. Apply language and style without routine compliance notices. Retain facts, quantities, units, decisions and acceptance requirements when shortening prose. Put a material limit beside the affected operation, with its impact and handling. Keep execution gaps in the existing work record and relevant handoff.

## Select a check

1. Resolve the canonical instruction and the actual Global/project/Skill/Plugin owner. Compare overrides and selected copies before adding a rule.
2. Select the relevant language profile. Check newly authored prose or changed passages, preserving protected text.
3. Use deterministic rules for known wording and punctuation. Review context-dependent advice, then correct the text or identify its protected source.
4. Read back changed bytes and recheck the affected passages. Compare discovery/loading and actual output behavior in the selected client when those stages change.

The shared `authored-style.cjs` flags six narrow groups of filler, generic liability wording and wordy English. Its default severity is `warning`; a selected personal/project profile can use `error` for a delivery check. Both modes report advice without automatic replacements. Preserve an established older profile when the selected base has no shared-style entry.

Examples for review:

```text
It is worth noting that the file was saved. -> The file was saved.
In order to update the file, obtain write access. -> Obtain write access to update the file.
值得注意的是, 檔案已儲存 -> 檔案已儲存
```

## Client-specific enforcement

Use Global for the personal default, a narrow project rule for a real project exception, and the relevant Skill for its portable fallback. Keep one maintained vocabulary/profile owner and generate Plugin copies from source.

For repository artifacts, run the selected local CLI before delivery and in an existing authorized CI gate where appropriate. Review failures against the source and protected-copy list. Test concise English, Taiwan wording, literal preservation, tool questions, progress and final output as separate cases.

For a supported local Codex client, inspect actual hooks, tool coverage and trust before selecting a hook. `Stop` receives `last_assistant_message`; `decision: "block"` creates a continuation prompt. `PreToolUse` can inspect supported local tool arguments. Test the exact surface and a bounded retry/stop condition before activation; retain existing authorization for every continuation. Keep hook installation and trust review in the owning client workflow.

## Checked sources

Checked 2026-11-02. Preserve source versions and observations with the relevant acceptance record.

| Source | Applied method |
| --- | --- |
| [OpenAI AGENTS.md](https://learn.chatgpt.com/docs/agent-configuration/agents-md) | Global/project layering, override selection and concise rules; GitHub review has its own documented rule section |
| [OpenAI hooks](https://learn.chatgpt.com/docs/hooks) | Actual event fields, tool coverage, trust and continuation semantics |
| [textlint configuration](https://textlint.org/docs/configuring/) and [CLI](https://textlint.org/docs/cli/) | Selected profiles, warning/error severity and local exit status |
| [Microsoft concise English](https://learn.microsoft.com/en-us/style-guide/word-choice/use-simple-words-concise-sentences) | Simple precise words, direct verbs and removal of empty phrases |
| [Japanese AGENTS.md practice, 2026-08-10](https://zenn.dev/akira_papa/articles/9a1be91ac478a1) | Explicit response language plus a small actual loading check |
| [Taiwan community Skill, v1.8.1](https://github.com/acchuang/zh-tw-humanizer/blob/main/SKILL.md) | Taiwan vocabulary, protected facts/literals and separate advisory patterns |
| [Historical Japanese CLI review report](https://github.com/openai/codex/issues/5113) | Check the specific review surface and current documentation when language behavior differs |
| [Korean tool-question report, 2026-11-02](https://github.com/openai/codex/issues/58761) | Include visible tool questions/options in language acceptance |
