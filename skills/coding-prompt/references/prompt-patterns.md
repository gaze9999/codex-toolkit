# Coding prompt patterns

Read this reference when creating reusable prompt templates or choosing an unfamiliar handoff shape. These are compact shapes, not required headings or repository rules. Replace bracketed fields with confirmed task content and omit irrelevant lines before delivery; keep the complete finished prompt in one `text` fenced block as specified by `SKILL.md`.

Execution and reporting expectations follow [Task intake, execution and reporting](../../agent-governance/references/task-execution-and-reporting.md). Consult that maintained source when revising these expectations and it is available; the compact patterns remain usable at a destination without this repository. Keep routine inherited guidance out of the prompt.

Separate the prompt, expected deliverable and report illustration with Markdown headings. Illustrations use placeholders, not observed results. Omit empty report sections, include useful recommendations when relevant, and retain the requested authority and scope. Necessary expansion needs a reason, affected slice, evidence and acceptance; proposals requiring a decision stay outside completed work.

## Implementation with a confirmed approach

### Prompt

```text
Complete [observable outcome] in [owned feature/module].
Use [relevant source path/section] for [specific fields or behavior]; preserve [confirmed interface or compatibility boundary].
Follow [confirmed approach] and retain [known concurrent edits or behavior].
Verify [task-specific acceptance] with [existing relevant check, if known]; report actual results, pending criteria and affected files.
[Unresolved decision] blocks only [dependent behavior]; continue independent authorized work.
```

### Expected deliverable

Changed code/artifact and observable behavior, with actual checks tied to the delivered state. Preserve failed/unverified acceptance and traceable open items; optional improvements remain proposals.

### Report illustration

```markdown
## Result

Implemented [behavior] in [files / symbols] against [requirement / effective decision].

## Verification

[Actual check and result], covering [criteria] for [checked state / environment].

## Unresolved work

[Existing ID / source, if available]: [issue or missing decision], affecting [behavior]. Evidence: [location / artifact]. Next action: [required action].

## Recommendations

[Evidence-based optional improvement], applicable to [condition]. Next step: [decision / action].
```

## Read-only investigation or review

### Prompt

```text
Investigate/review [specific trigger or question] in [bounded source/revision]. Keep the work read-only.
Compare [expected behavior from identified requirement] with the actual call/state/data flow.
Return concrete findings with file/symbol, trigger, impact and evidence, or no findings. Separate confirmed defects from unresolved questions.
Identify the smallest next action and any verification gap; do not infer approval to implement repairs.
```

### Expected deliverable

Concrete findings or no findings, with source/revision coverage, triggers, expected/actual behavior, impact and evidence. Separate confirmed defects, unresolved questions and proposed repairs.

### Report illustration

```markdown
## Findings

[Finding / no findings], for [checked source state and scope].
[File / symbol / existing ID]: [trigger], expected [behavior], observed [behavior], impact [consequence].

## Evidence and coverage

[Inspected locations / actual checks and results]. [Uncovered criterion, if applicable].

## Unresolved questions

[Missing requirement / evidence and affected conclusion]. Next action: [needed confirmation].

## Recommendations

[Smallest proposed repair or useful improvement], based on [evidence]. [Approval / verification needed before implementation, if applicable].
```

## Read-only implementation planning

### Prompt

```text
Propose an implementation plan for [observable outcome] in [owned feature/module]. Keep the work read-only.
Use [necessary source/section] and preserve [confirmed interface or compatibility boundary].
Return the recommended approach, reasons/tradeoffs, affected scope, dependencies and observable acceptance.
Identify [material unresolved decision] and what it blocks; distinguish required work from optional improvements and any expansion needing authorization.
```

### Expected deliverable

A reviewable plan grounded in current sources, with necessary changes, scope, dependencies, acceptance and decisions still needed.

### Report illustration

```markdown
## Proposed approach

[Approach], based on [source / inspected state], chosen because [reason / tradeoff].

## Scope and acceptance

[Affected feature / files and necessary dependencies]. Completion means [observable criteria and proposed checks].

## Decisions needed

[Unresolved decision and affected work]. Next action: [decision owner / confirmation].

## Optional improvements

[Evidence-based option, applicability and next step].
```

## Continuing work with another owner

### Prompt

```text
Continue [authorized outcome] from [current source/revision and relevant uncommitted state].
Own [coupled scope]; [other owner] retains [neighboring scope or shared decision].
Confirmed decisions: [only decisions that change execution, with current source pointers].
Accepted work: [effective artifacts and checked state]. Pending work: [unfinished criteria, returned/pending acceptance, blockers and updates not yet adopted].
Preserve [independent edits and must-retain evidence]. Reconcile [prior ownership or changed baseline] before dependent writes.
Complete [remaining acceptance and focused checks], then report checked source state, criterion status, actual results and unresolved items.
```

A handoff transfers useful state; it does not authorize a new chat, cross-chat messages, external actions or broader ownership. Include failed approaches only when the next owner would otherwise repeat them. Keep Main's acceptance responsibility and distinguish source inspection from runtime or deployment verification.

### Expected deliverable

For authorized continuation, complete the remaining implementation and checks. For handoff-only work, deliver effective state and evidence for the next owner. Preserve changed decisions, outstanding acceptance and traceable next actions.

### Report illustration

```markdown
## Result and reusable work

[Delivered result / handoff state]. Reused [accepted artifact / evidence] for [current checked state].

## Verification

[Actual checks and results]. [Previously accepted evidence that still applies].

## Pending acceptance

[Existing ID / source and remaining criterion], owned by [owner, if applicable]. Evidence: [location / artifact]. Next action: [required action].

## Recommendations

[Useful proposal and supporting evidence], requiring [next decision / action].
```
