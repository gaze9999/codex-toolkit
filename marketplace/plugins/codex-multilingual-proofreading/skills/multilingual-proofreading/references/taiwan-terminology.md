# Taiwan terminology maintenance

Read for requested additions or revisions to a Taiwan Chinese terminology profile, including textlint/prh vocabulary. Start from the existing vocabulary, source notes and configuration; maintain their format rather than introducing another dictionary or fixed record schema.

## Select evidence by meaning

- Prefer Taiwan official sources for terminology evidence. Use the Ministry of Education dictionaries for general meanings and the National Academy for Educational Research's terminology portal for the relevant discipline and Chinese/English sense. Choose the dictionary/collection for the audience; a historical entry or an unrelated academic discipline does not establish a current software usage.
- Match the actual meaning, original-language term, audience and field. Follow original entries rather than relying on search snippets or a secondary copy. Product labels and specification-defined strings follow their authoritative product/project source. Community usage can supplement missing development context, with its origin retained.
- Classify the adopted wording as official terminology, product/project usage or personal preference. A user's punctuation or preferred synonym is not an official language rule. Keep accepted alternatives when the source permits them; record unresolved conflicts instead of declaring every alternative incorrect.

Reuse compatible previously collected evidence. Refresh the affected original source for missing meaning, changed versions, conflicts or unclear licensing; ordinary prose correction needs no new terminology research.

## Record and apply selectively

Keep sufficient provenance in the existing comments/source documentation: suggested term and original-language sense when useful, applicable context, authority category, source ID/direct URL, source version or date when available, check date, and relevant license/attribution conditions. Preserve source dates separately from the date of checking. These are evidence requirements, not mandatory parser fields.

Use narrow context patterns for ambiguous terms and retain positive conversion cases, accepted wording and counterexamples that must remain unchanged. When context cannot be matched reliably, provide manual advice instead of an automatic replacement. Preserve quotations, code, identifiers, names and authoritative UI/specification text. Do not convert all occurrences or copy dictionary definitions into correction rules by default.

Check the selected rule format and its examples, then verify the complete lint/fix chain for interacting rules. Synchronize only authorized local assets through their maintained installer, preserving differences/backups; compare CLI and MCP configuration/results when both are affected. A source edit, preview, saved file and client reload are separate states.

## Check the selected material's license

Before downloading, copying, transforming or distributing source data, read the selected dataset's current usage terms and any entry-specific restrictions. Preserve required attribution, version and notices, and follow transformation/redistribution conditions. Public access and an official domain alone do not establish permission for bundling a dictionary. Where rights remain unclear, keep a source link and an independently authored context decision rather than redistributing source material.

Primary entry points checked 2026-10-10:

| Source | Use and licensing evidence |
|---|---|
| [MOE public dictionary licensing](https://language.moe.gov.tw/001/Upload/Files/site_content/M0001/respub/index.html) | Select the dictionary by its audience and meaning. The listed Mandarin dictionaries use CC BY-ND 3.0 Taiwan with dictionary-specific usage instructions. |
| [MOE Concise Dictionary usage instructions](https://language.moe.gov.tw/001/Upload/Files/site_content/M0001/respub/conciseddict_10312.pdf) | Require attribution/version and retained instructions; individual entry content has restrictions on modification. Inspect the selected dictionary's own terms for other material. |
| [NAER terminology portal](https://terms.naer.edu.tw/) | Match discipline, collection, sense and accepted equivalents. |
| [NAER open-information declaration](https://terms.naer.edu.tw/mysite/about/2/) | Allows covered reuse with source attribution, subject to its exclusions and separately restricted third-party material. Check the selected material before redistribution. |

These entry points support source selection; specific rules still need their actual term/context evidence. Research or a dictionary license does not authorize installation, publication or external processing of private text.
