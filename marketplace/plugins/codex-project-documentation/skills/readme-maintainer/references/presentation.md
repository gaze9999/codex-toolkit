# README learning and presentation

Read when restructuring a README's teaching flow, examples or visual presentation. Keep the README focused on a reader's first useful result.

## Choose a reader path

- Start with what the project does and who uses it. Follow with the shortest useful setup and common operation, then link optional configuration, advanced tasks and development details.
- Resolve intended public readers even while development is private. A player/product reader may need a short introduction and usable entry point, while an integration user or contributor needs different technical detail. Place versions, framework/architecture, engineering evidence and development procedures where they help that reader; retain material compatibility and license information. Choose by the request and actual audience, not a fixed public README exclusion list.
- For a toolkit, distinguish an ordinary user, an integration user and a contributor. A compact choice table may route CLI, wheel, Plugin and MCP users before installation commands. Do not require every reader to build all packages or install every optional tool.
- Order sections by the reader's decisions, not the order files were created. A common sequence is purpose, interface choice, requirements/quick start, examples and expected output, detailed guides, development/verification and license. Adapt it to the actual project rather than forcing empty headings.
- Keep one representative working path prominent. Link full command catalogs, API schemas, troubleshooting and release procedures instead of repeating them. Commands, arguments, paths and expected artifacts must match actual source and checks.
- Treat size as a review signal, not a quota. A single-purpose README is often 300-800 English words or roughly 600-1600 Chinese characters; a multi-interface toolkit may need more. Shorter useful READMEs are fine. Preserve necessary steps, support limits and destructive/write behavior; split detail by real reader need.

## Examples and images

- Treat reading as a user flow: clear heading hierarchy, stable descriptive links, copyable commands, readable tables and short nearby explanations. Avoid wide comparison tables, image-only instructions and important content hidden in collapsed sections. Check relevant GitHub/web/mobile rendering when layout changes, not just source length.

- Use small, safe fixtures or placeholders. Show the input, exact command and useful output/artifact. Mark illustrative output as an example; do not fabricate a successful execution, UI screenshot or deployment.
- Include an image only when it teaches a result, UI operation or non-obvious architecture more clearly than text. A CLI-only tool may need just a code example or small diagram.
- Prefer an existing current screenshot/demo or an authorized reproducible capture. Redact account names, private paths/endpoints, customer data, tokens and session information before distribution. Record relevant version/state when it changes the interpretation.
- Keep assets repository-relative, provide informative alt text and check rendering/link closure. A small overview belongs near the introduction or relevant operation; move large walkthroughs and galleries to detailed docs. Avoid badges or decorative images without a useful verified target.

## Explain instead of disclaim

Describe supported behavior, dependencies, input/output, side effects and concrete support limits. Remove generic liability disclaimers, defensive comparisons, repeated exclusions and maintenance-history prose when they do not help the reader use the tool. Keep actual overwrite/delete risks, account/data boundaries, compatibility requirements, unverified claims and legal notices where they matter. README editing never changes a LICENSE or third-party notice without authorization.

Check the key route, commands, expected outputs, internal links and relevant assets with the smallest sufficient available checks. Source/link review, real execution, rendering and native-platform verification are different results; report them honestly.

## Optional outline references

Use only the relevant pattern and remove inapplicable parts. These are organization examples, not required headings or finished claims.

| Reader goal | Useful order |
|---|---|
| Run a CLI tool | Purpose → requirements → shortest command → input/output example → write behavior/options → advanced guide → license |
| Import a Python library | Purpose → supported Python/API version → installation → small import example → API/data format reference → compatibility → development/license |
| Install a Plugin or MCP | Capability → choose the appropriate interface → installation → account/runtime prerequisites → first real use → update/remove guide → evidence limits/license |
| Understand a multi-tool repository | Purpose → interface choice table → one quick-start route per interface → linked tool guides → contribution/tests → license |

During maintenance, preserve an effective existing organization. Patch the affected sections/examples and their live references. A requested audit is read-only; a small fix does not authorize rewriting the full README, renaming commands or reorganizing the project. Substantial restructuring needs explicit scope or a concrete demonstrated usability gap within the authorized task.
