# Taiwan terminology maintenance

Read for requested additions or revisions to a Taiwan Chinese terminology profile, including textlint/prh vocabulary. Start from the existing vocabulary, source notes and configuration; maintain their format rather than introducing another dictionary or fixed record schema.

## Select evidence by meaning

- Prefer Taiwan official sources for terminology evidence. Use the Ministry of Education dictionaries for general meanings and the National Academy for Educational Research's terminology portal for the relevant discipline and Chinese/English sense. Choose the dictionary/collection for the audience; a historical entry or an unrelated academic discipline does not establish a current software usage.
- Match the actual meaning, original-language term, audience and field. Follow original entries rather than relying on search snippets or a secondary copy. Product labels and specification-defined strings follow their authoritative product/project source. Community usage can supplement missing development context, with its origin retained.
- Classify the adopted wording as official terminology, product/project usage or personal preference. A user's punctuation or preferred synonym is not an official language rule. Keep accepted alternatives when the source permits them; record unresolved conflicts instead of declaring every alternative incorrect.

Reuse compatible previously collected evidence. Refresh the affected original source for missing meaning, changed versions, conflicts or unclear licensing; ordinary prose correction needs no new terminology research.

## Checked government evidence

Checked 2026-11-02. Use each source for its stated scope, with the original publication date retained below. The MOE comparison explains regional equivalents for the same concept; its FAQ directs interpretation by meaning. MODA's bilingual catalog supplies policy/technical names, and its explainers supply concept distinctions.

| Source | Adopted evidence and use |
| --- | --- |
| MOE [comparison, page 4](https://dict.concised.moe.edu.tw/appendix.jsp?ID=54&la=0&page=4&powerMode=0), [page 5](https://dict.concised.moe.edu.tw/appendix.jsp?ID=54&la=0&page=5&powerMode=0) and [interpretation FAQ](https://dict.concised.moe.edu.tw/qa.jsp#qg6) | Check the selected computing sense for 晶片, 剪貼簿, 解析度, 解除安裝, 主機板, 桌布, 簡訊 and 人工智慧. The appendix credits material authorized by 中華文化總會. Link the evidence and author correction patterns/examples independently. |
| NAER [Computer Hardware](https://pedia.cloud.edu.tw/Entry/Detail?title=%E9%9B%BB%E8%85%A6%E7%A1%AC%E9%AB%94), Education Encyclopedia, 2000-12; [network operating system](https://pedia.cloud.edu.tw/Entry/Detail/?title=%E7%B6%B2%E8%B7%AF%E4%BD%9C%E6%A5%AD%E7%B3%BB%E7%B5%B1), Dictionary of Information and Communication Terminology, 2003-06 | Verify hardware, RAM/ROM and operating-system/storage meanings. These Education Cloud entries retain their own attribution and CC BY-ND 3.0 Taiwan notice. Use current product documentation for implementation details. |
| MODA [bilingual glossary](https://moda.gov.tw/information-service/bilingual-glossary/1391) | Match the named concept and catalog category, including cybersecurity incidents and electronic/digital signatures. Preserve legal and product names. |
| MODA [metadata explainer](https://moda.gov.tw/press/dictionary/19328), published/updated 2026-04-02 | Prefer 詮釋資料 for authored dataset metadata prose; preserve product-specific 中繼資料 and the `metadata` Symbol. |
| MODA [electronic-signature technology](https://moda.gov.tw/press/dictionary/12794), published 2024-05-17, updated 2025-03-06 | Keep electronic signature and digital signature distinct. Use the applicable current legal source when legal effect matters. |

## Context decisions

| Subject | Editing decision |
| --- | --- |
| Memory and storage | Choose 記憶體 for RAM/ROM or the verified memory concept. Choose 儲存裝置/儲存設備 for storage hardware. Check an isolated 存儲器 before changing it. |
| Video | Use 影片 for recorded content/files and 視訊 for calls/conferencing. Retain the existing context-specific patterns. |
| Project, code and configuration | Use 專案 for project work and 程式碼 for code. Retain 清單項目, 識別代碼 and 資源配置. |
| Image and mirror | Use 映像/映像檔 for container/disk images and 鏡射 for a verified mirroring operation. Keep optical mirrors and product names. Review isolated 鏡像 manually. |
| General editing preferences | Choose 資料/數據, 支援/支持, 使用者/用戶端/用戶 and 改善/最佳化/優化 by meaning and product context. Preserve policy names such as 數據賦能. |
| Limited rollout, profile preference | This Taiwan Chinese profile flags 試點 for contextual review and prefers 先行驗證, 試行 or 試辦 by meaning. This is a profile choice, not an official terminology claim. Preserve formal names and source quotations; never select a synonym automatically. |
| Integration and use | Use 串接/介接 for software connections and 情境 for use cases. Express implementation as 導入, 部署, 正式上線 or 落實 by action; preserve other meanings of 對接, 場景 and 落地. Describe the actual feedback/recovery steps instead of guessing from 閉環. |
| Agent | Keep AI Agent and Agentic AI distinct using the maintained agent glossary. Preserve official source variants such as 代理型 AI when quoting that source; choose authored terms by responsibility. |
| Signatures and security | Keep 電子簽章/數位簽章, 資安事件 and 漏洞/弱點 distinct by the actual mechanism and event. These choices require semantic review. |

## Maintained owners

| Layer | Responsibility |
| --- | --- |
| Global/project instructions | Audience, output style and real project exceptions |
| This reference and the agent glossary | Source classification, meaning and accepted alternatives |
| `terms.yml` | Reviewed deterministic patterns with conversion and preservation examples |
| `taiwan-style.cjs` / `authored-style.cjs` | Contextual agent/style advice, with manual decisions and selected severity |
| Local CLI / MCP | The same selected engine/profile; use CLI for local batches and MCP for required structured client access |
| Plugin | Generated copies of canonical guidance/resources, with source hashes and native installation handled separately |

Keep personal choices in the selected private profile and company choices with their approved owner. Apply wording/style directly; explain a terminology decision only when it changes meaning, operation or the result.

## Record and apply selectively

Keep sufficient provenance in the existing comments/source documentation: suggested term and original-language sense when useful, applicable context, authority category, source ID/direct URL, source version or date when available, check date, and relevant license/attribution conditions. Preserve source dates separately from the date of checking. These are evidence requirements, not mandatory parser fields.

Use narrow context patterns for ambiguous terms and retain positive conversion cases, accepted wording and counterexamples that must remain unchanged. When context cannot be matched reliably, provide manual advice instead of an automatic replacement. Preserve quotations, code, identifiers, names and authoritative UI/specification text. Declare exact protected prose in the existing literal filter or present it as code/blockquotes for prh; ordinary quotation marks alone do not establish a protected range. Do not convert all occurrences or copy dictionary definitions into correction rules by default.

Check the selected rule format and its examples, then verify the complete lint/fix chain for interacting rules. Synchronize only authorized local assets through their maintained installer, preserving differences/backups; compare CLI and MCP configuration/results when both are affected. A source edit, preview, saved file and client reload are separate states.

## Agent architecture vocabulary

For requested agent terminology, use the [maintained agent glossary](https://github.com/gaze9999/codex-toolkit/blob/main/skills/agent-governance/references/agent-terminology.md) when available. Preserve English names/IDs and source-specific Chinese translations. Keep `AI 代理程式`, `AI 代理人` and `AI 代理` as accepted alternatives when their source/audience requires them.

Agent Instructions are `工作規範`; governance concerns policy/accountability/identity/risk. Delegation assigns work, while an actual runtime handoff transfers active handling/control. Harness is execution control around the model; sandbox is isolated compute. Compaction, memory and checkpoints have different responsibilities, though an implementation may combine them. Observability records operational evidence; evaluation applies task criteria. MCP, A2A, A2UI and AG-UI cover different primary boundaries and can compose.

Keep ambiguous aliases advisory without automatic fixes. Limit patterns to clear agent contexts, preserve quotes/code/UI copy and test accepted alternatives.

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
