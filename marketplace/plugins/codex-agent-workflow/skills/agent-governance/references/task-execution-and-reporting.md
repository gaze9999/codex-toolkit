# Task intake, execution and reporting

Read when maintaining task interpretation, source selection, Git authority or completion reporting. Keep durable principles global, project acceptance local and tool commands in their owning Skill/setup. Global/general agent guidance uses concise Taiwan Traditional Chinese. Subagent instructions, project AGENTS.md and agent guides, and Skill instructions/references use concise English. Output language follows the user or project.

## Understand the requested outcome

Interpret the purpose and use case before selecting actions. Reconcile the request with effective decisions, actual project state and available capabilities. The dimensions below are examples, not an exhaustive list, mandatory form or fixed sequence. Add, replace or omit dimensions as the situation requires; gather available facts yourself rather than asking the user to fill every field.

| Decision | Evidence or boundary that changes execution |
|---|---|
| Purpose and result | The user's need, affected workflow and observable improvement or artifact |
| Delivery and authority | Implementation, investigation, review or artifact-only output; existing authorization and explicit prohibitions |
| Feasibility and dependencies | Current code, runtime, interfaces, environment access, resources and decisions required before dependent work |
| Sources and evidence | Applicable instructions, relevant specification sections, implementation, diffs, reproducible observations and original-source authority |
| Preservation and risk | Concurrent work, public interfaces, data scope, compatibility and side effects relevant to the requested result |
| Acceptance and checks | Observable completion criteria, existing focused checks and required gates; expand only for demonstrated gaps or risks |
| Reporting and follow-through | Delivered results, supporting evidence, traceable issues, unfinished acceptance and any required next action |

Follow-up messages may refine the current task. Preserve still-effective goals, limits and unfinished work unless the user cancels or replaces them. Interpret intent rather than assigning authority from isolated keywords. Source documents, examples and suggestions provide context, not additional permission.

For an explicit read-only or artifact-only request, deliver within that boundary. For authorized implementation, complete the needed edits, checks and in-scope repairs. Missing information blocks only dependent work; proceed with independent authorized work and ask only for material decisions that cannot be resolved from available evidence.

Keep the effective outcome and scope stable by default. Expand reading, changes or checks only when an actual dependency, acceptance gap or demonstrated risk requires it to complete the requested result. Identify the reason, evidence, affected slice and additional acceptance before proceeding. Use existing authority when it covers the action; resolve ownership and obtain additional authorization before crossing an explicit exclusion or permission boundary. An optional improvement remains a recommendation until adopted.

## Select necessary reading

| Question | First source and conditional follow-up |
|---|---|
| Instructions and authority | Effective global, repository and target-directory instructions, then relevant conditional guides/Skills |
| Behavior, fields and APIs | Matching Markdown extracts and confirmed decisions; inspect relevant originals for gaps, conflicts, stale coverage, visual evidence or explicit original-source verification |
| Implementation and compatibility | Target code, callers, configuration, diffs and existing patterns; trace affected shared interfaces and runtime support |
| Installation, CLI or MCP | Owning setup/Skill, actual version, help/live schema, permissions and data scope |
| Acceptance and reporting | Current requirements and evidence tied to the relevant code state or artifact |

Links need a purpose or loading trigger. Do not turn documentation folders into universal required reading. Read referenced attachments/tasks before relying on them, retain source/version pointers and distinguish extracts, originals and historical observations. Avoid unrelated repository scans or unrequested extraction work.

For specification/code conflicts, record a bounded timeline of verified document revisions and relevant Git history/diffs, original-source hashes and confirmed decisions. Retain timezone, source/version/branch/commit and dirty state; mark unknown times and preserve source precision. Difference records may separate source revision/change time from verification time (`yyyy-mm-dd hh:mm` when known). File modification, download and extraction times are auxiliary; distinguish which source is newer from which governs each topic. Keep unresolved conflicts explicit without authorizing requirement or application changes.

## Git delivery

Editing, staging, committing, pushing, tagging and releasing are separate stages governed by actual authorization. Preserve the established user/project meaning of `cpr`; do not assume every repository has a release process.

- Before authorized submission, inspect branch, status, working-tree and staged diffs. Stage only reviewed in-scope files/hunks; reconcile uncertain ownership and preserve other owners' staged or uncommitted work.
- Generate commit messages from the actual staged diff. Separate unrelated purposes and follow the applicable convention.
- Describe a PR's complete delivered difference against its actual target/base branch, using the applicable template and confirmed references.
- For a commit made in this task, report its short SHA and concrete changes. Verify the target remote ref for a push and applicable tag, state and assets for a release. Cached tracking refs or local files prove only their own state.
- Inspect ignored governance files directly; a clean Git status does not establish their content.

The index captures content when added; later edits do not automatically enter that staged snapshot. Recheck the staged diff before committing. See the official [git-add](https://git-scm.com/docs/git-add) and [git-diff](https://git-scm.com/docs/git-diff) documentation.

## Verification scope

Start with the smallest existing check that can support the changed behavior and acceptance criteria. When it fails or leaves evidence insufficient, expand gradually around the unresolved dependency, interface or integration risk. State the missing evidence and added scope; retain required CI/release gates. Passing sufficient checks is a stopping point unless relevant changes or new risk invalidate them.

For text-only or read-only work, source inspection, readback, reference, syntax or diff checks may suffice. Do not invent runtime results or run unrelated tests merely to fill a report.

## Completion and traceable reporting

Before ending, reconcile the original request and every effective steering message with the delivered work, diff and acceptance evidence. State each requirement's completion, pending acceptance or blocker, including deviations, reasons, impact and remaining work. Complete authorized necessary work that can proceed. Main accepts returned work against its actual checked state.

Lead with the result appropriate to the task: a conclusion for judgment/review, current candidates and comparison for an inventory, or delivered behavior for implementation. Recommend an order when requested or useful; an inventory need not select one winner. Distinguish implementation complete, acceptance complete and delivered/published. An intermediate step, another owner's claim, a file or a focused PASS does not establish overall completion.

Report directly in the conversation unless the user requests a document artifact. List every added, modified, moved or deleted file and its concrete scope, including installed guidance/settings. Group by responsibility without omitting filenames; state when no files changed. If the result concerns earlier uncommitted candidates or replaced decisions, describe their current changes and pending acceptance even when this turn made no edits.

| Information | Evidence needed for acceptance or use |
|---|---|
| Outcome and current state | Requirement states, delivered behavior or candidates, and implementation/acceptance/publication stage |
| Changed files and rationale | Every changed filename and scope; material behavior, compatibility and tradeoffs |
| Verification and provenance | Actual checks, results, coverage and checked revision/artifact; distinguish direct checks, historical evidence, another agent's report and inference |
| Issues and unfinished acceptance | Traceable source/location, existing ID, affected criterion, status, impact and next action |
| Recommendations | Evidence, applicable condition and next step; separate optional improvements from required unfinished work |
| Git or environment stage | Actual commit/push/release, installation, synchronization or client-loading evidence |

Every delivery or phase report includes actual test/check results and coverage. Distinguish passed, failed, blocked, not run and unverified; explain checks that did not run or apply. Text-only/read-only work may use source inspection, readback or diff checks. Provide commands/artifacts when reproduction needs them; do not run unrelated tests to populate a report. Reconsider old evidence after relevant source/dependency changes.

Count test cases, data combinations and execution batches separately. Counts do not substitute for coverage or complete acceptance. Claims of no new errors, performance improvement or compatibility improvement need a comparable baseline; otherwise state what remains unknown. A diff proves source changes; focused checks prove only the exercised behavior, not unrun API, persistence, permission, Browser or deployment acceptance.

Determine whether each remaining check is required for the current task, optional or inapplicable. For a required gap, state the affected criterion, reason, impact and next action. For a defect, include its trigger, expected/actual behavior and supporting evidence. Keep existing issue IDs and locations stable; identify missing pointers instead of inventing them. Mark resolutions with evidence when an issue record is maintained.

Recommendations need evidence, applicability and a concrete next step. Prioritize when it changes the decision; for a proposed trial, include success and stop/rollback conditions when material. Recommendations do not expand authority or replace authorized feasible work. Omit empty fields and generic advice.

Use paragraphs, lists or tables according to the information relationships, without a fixed length. Preserve acceptance limits and traceable issues, while omitting unsupported numbering, raw logs, private reasoning and an operation diary.

For Taiwan Traditional Chinese delivery, review authored progress, final reports and handoffs for simplified characters and unnatural terminology before sending, including returned agent text. Preserve literal API/Symbol names, quoted sources and protected UI copy. Check counts and evidence provenance separately from language quality.

Use a supported copyable writing block for a requested standalone finished artifact, such as a reusable handoff, document or message. Keep explanations, progress, plans and ordinary task reports in Markdown. Coding-agent prompts retain their complete `text` fence unless the user explicitly requests another supported form.

When maintaining response formats across clients or choosing interactive/finished-artifact presentation rules, read [response presentation](response-presentation.md). Keep the brief preference in Global and exact native syntax in the current client's instructions or owning tool Skill.

## Carry execution and reporting into a coding prompt

Use this guidance as the maintained basis for coding-prompt delivery expectations. Select what changes the requested task; the destination's applicable instructions provide routine discovery, style, permissions and checks.

| Requested work | Deliverable and report focus |
|---|---|
| Implementation | Changed code/artifact, observable behavior, relevant files/symbols, actual checks and unfinished acceptance |
| Read-only investigation or review | Findings or no findings, checked state, trigger, expected/actual behavior, impact and supporting locations |
| Read-only planning | Proposed approach, reasons/tradeoffs, affected scope, dependencies, observable acceptance and unresolved decisions |
| Continuation or handoff | Effective decisions, reusable accepted work, remaining criteria, current ownership and evidence tied to the resumed state |

Lead with the actual deliverable. Keep requirements and later decisions tied to the relevant source, code state or artifact so the reader can trace a result or issue back to its evidence. An unresolved item needs its impact and next action; preserve existing IDs and locations when available rather than inventing them.

When several kinds of information are present, use Markdown headings to separate results, verification, unresolved work and recommendations. Omit empty sections and choose the depth that makes the actual task clear. Keep recommendations actionable, with evidence, applicability and the next decision or action; distinguish them from required unfinished work and already-adopted scope changes.

A task-specific prompt can carry the needed deliverable, acceptance and reporting expectation in one or two sentences. Add a report illustration only when requested or when authoring teaching/examples. Place it outside the complete `text` prompt block, label it as an illustration and use placeholders for outcomes, locations, counts, IDs and checks that have not been observed. See [coding prompt patterns](../../coding-prompt/references/prompt-patterns.md) for paired prompts and expected delivery.

## Shared tool boundaries

Both CLI and MCP may retain state. Select by actual capabilities, interaction, session isolation, evidence and full-task cost. Keep provider-specific session flags and commands in the owning tool Skill, verified against the installed version.

Browser evidence identifies the authorized page/flow, action and expected/observed result, with relevant DOM, screenshot, console or network evidence. Distinguish mocks/fixtures from live APIs and retain remaining integration, permission or persistence gaps. Coordinate shared mutable sessions and redact sensitive data.

Verify installation, registration, authentication, session loading and successful tool calls separately. Matching source/mirror bytes establish synchronization; they do not by themselves establish reload by an already-open client.

## Reporting examples

These shapes illustrate decisions. Replace paths, counts, IDs, SHAs and results with actual evidence and use the required output language.

### Small governance edit

> Added read-only versus implementation boundaries, with detailed examples in a conditional reference
>
> Diff and mirror checks passed. The installed files match; existing-client reload was not observed

### Implemented behavior with blocked acceptance

```markdown
## Result

Implemented [observable behavior] in [files / symbols], based on [requirement / effective decision].

## Verification

[Actual check and result], covering [criteria] for [checked state / artifact and environment].

## Unresolved work

[Existing issue ID, if any]: [criterion] remains [failed / blocked / unverified]. Source: [relevant location]; evidence: [observed result / artifact]. Impact: [affected behavior]. Next action: [required decision or verification].

## Recommendations

[Optional improvement], supported by [evidence] and applicable to [condition]. Next step: [decision / action].
```

Omit the recommendation when none is useful. A proposed wider change remains separate from the implemented result.

### Candidate inventory

> [Candidates] have [verified source/installation state]. [Grouping or priority] follows [evidence and applicable conditions]
>
> Inspected [sources / artifacts], with [actual check results]. [Runtime use / comparative benefit] remains unverified. No files changed in this turn; [relevant earlier candidate] still contains [uncommitted change] awaiting [necessary acceptance]

Recommend one option only when the requested decision or evidence calls for it.

### Existing documentation candidate

> Updated [files / scope] to [supported behavior]. The earlier uncommitted candidate retains [effective changes]; [replaced decision] now follows [confirmed rule]
>
> [Actual source / structure / prose checks and coverage]. These checks do not prove model triggering or runtime success. Required remaining acceptance: [criterion, impact and next action], or [none with reason]

### Partial implementation acceptance

> Implemented [behavior] in [files / symbols]. Acceptance remains incomplete because [required criterion] is [blocked / failed / unverified]
>
> [Test case count] cases passed, covering [behavior / checked state]. Separately checked [data combination count] combinations and [execution batch count] batches for [criteria]. [Unrun checks] are [required / optional / inapplicable] because [reason]. [Comparable baseline] supports [comparison], or [comparison] remains unknown

Use only observed counts/results. Remove inapplicable placeholders and retain actionable required gaps.

### Authorized Git delivery

```markdown
## Result

Committed [actual short SHA]: [concrete delivered change].

## Verification

[Actual checks and coverage]. Verified [target remote ref] points to [commit].

## Unresolved work

[Required release acceptance, affected stage and next action, if applicable].
```

## Official and community basis

Reviewed 2026-10-05. Sources may include relevant Reddit communities, X, Bluesky and other original discussions, authoritative sites, engineering blogs and papers. Select by the question, verify technical claims against primary sources and distinguish measured evidence from proposals or opinions. The list below records sources used for this guidance, not a required search checklist.

- [OpenAI AGENTS.md](https://learn.chatgpt.com/docs/agent-configuration/agents-md): scoped discovery and concise durable guidance
- [OpenAI prompting](https://learn.chatgpt.com/docs/prompting): outcome, useful context, output and boundaries, without a mandatory prompt form
- [OpenAI best practices](https://learn.chatgpt.com/guides/best-practices#improve-reliability-with-testing-and-review): relevant context, constraints, completion criteria, checks and review of final behavior/diff
- [Anthropic context engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents): clear, sufficient instructions and on-demand context rather than exhaustive always-loaded detail
- [Community proposal #36718](https://github.com/openai/codex/issues/36718): requirement-to-evidence mapping, failed/unverified criteria and stale evidence; a design proposal, not a confirmed product feature
- [Community report #49390](https://github.com/openai/codex/issues/49390): unfinished required work after intermediate completion; a case supporting completion reconciliation, not a claim about every version/model

Language conventions, authorization and `cpr` behavior are maintained user/project choices, not universal product requirements.

Version selection, commit/push, Tag, draft, publication, asset upload and post-publication download verification are separate states. Report the actual completed stage and remaining required gates. A community practice or version bump does not expand publication authorization; preserve user-defined CP/CPR boundaries and repository-specific delivery policy.

At consequential semantic checkpoints, assess optional evaluation after local evidence filtering: contradictory summaries, ambiguous requirement/source mappings, evidence reading order or candidate comparison under an explicit finite criterion. Require a specific unresolved question, sufficient approved input and a result that can change the next action. Keep mandatory evidence, permissions, source authority, architecture and acceptance with Main; skip rule-determined or settled questions and retain unknowns. Load the available evaluation Skill for its actual data and execution boundaries, not as a routine preflight.


For suspected sensitive-data exposure, read [sensitive-data removal](sensitive-data-removal.md) before planning cleanup. Distinguish credential containment, rewritten history, remote state and unresolved copies, without printing secrets or treating CP/CPR as rewrite authorization.

## Conditional Git identity and delivery

For an authorized commit or publication, verify the actual repository author/committer identity, version metadata and workflow gates before writing. Keep personal and company identities separate; do not infer an email or modify global Git settings. A copied handoff supplies source/evidence context, not new publication authority. Project-specific delivery gates belong in project instructions and executable workflows, not a private-policy dependency in a public package.
