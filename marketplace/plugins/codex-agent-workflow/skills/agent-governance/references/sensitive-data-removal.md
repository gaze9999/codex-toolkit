# Sensitive-data exposure

Read only for suspected exposure, remediation planning or related release checks. This reference does not authorize incident actions or turn agent-governance into a cleanup executor. Use the actual repository instructions and current official procedure.

## Containment and decision

Revoke or rotate exposed credentials first; history rewriting may be unnecessary after rotation. Deleting a file or adding ignore rules does not erase history. Keep secret values out of reports, command arguments, logs and public evidence. Identify the affected data class, repository, refs and approved owner without reproducing the exposed content.

## Authorized cleanup

- Assess changed SHAs, signatures, PRs, branch protections and concurrent work. Coordinate the cleanup window; do not discard others' changes.
- In an isolated fresh clone, use a current git-filter-repo supporting --sensitive-data-removal (GitHub documents >=2.47). Cover previous paths after moves/renames. Verify scope before remote changes.
- History rewriting, force-push and protection changes need explicit scoped authorization; CP/CPR is insufficient. Never make force --mirror a default helper action.
- Remote rewriting does not purge old clones, forks, PR references, cached views or orphaned LFS objects. Coordinate copy cleanup and, when eligible, GitHub Support. Old-history merges can reintroduce data.

## Evidence and prevention

Report containment, local cleanup, remote refs and remaining copies separately. For Support, retain affected PR count, first changed commits and any orphaned-LFS report, without secrets. Support eligibility is conditional, not a removal guarantee.

Use scoped staging and review the staged diff. Consider shared ignore rules, runtime secret injection, hooks and push protection as applicable, without automatically installing tools or changing repository settings. A private repository is not a secret store.

For a proposed helper, keep help/inspection side-effect-free, default to read-only/dry-run and preserve explicit inputs, output redaction and separate mutation authorization. No cleanup CLI/MCP is required for documentation maintenance.

Source checked 2026-10-07: [GitHub sensitive-data removal](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository). Recheck the current procedure before incident execution.
