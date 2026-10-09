# Version and Tag strategy

Read for a requested Tag policy, version checkpoint or authorized Tag delivery. Use actual user/project shorthand definitions and release policy; keep ordinary branch pushes available without a Tag for every change.

## Choose a checkpoint and version

Tag a useful reproducible baseline, supported package or completed milestone when requested or required by the project. Version semantics and publication cadence are separate: patch releases can be useful, and minor-only milestones are a project choice. Do not impose a fixed count of commits, Tasks or Skills before tagging.

Inspect the maintained version source, previous relevant Tags, component metadata and workflows. Keep component and aggregate versions independent. For SemVer, select patch/minor/major from the supported interface change and apply the project's pre-1.0 stability policy. Preserve an established alternative scheme. If Tags are the version source, compare the previous relevant Tag and actual changes rather than relying on name sorting alone.

Use the established full version format, normally `vX.Y.Z`. Prefer annotated Tags for maintained checkpoints; signing follows the project's supported identity and policy. Current private access and planned public scope are separate, with boundary checks selected for what will be exposed.

## Deliver and verify

- Resolve the exact reviewed commit, identity, branch/worktree, remote and authorized stages. Keep parallel changes and the existing index intact. Version edits or package preparation do not authorize remote publication.
- Inspect Tag-triggered automation and applicable checks before pushing. A Tag that deploys or publishes a package needs that action's authorization. Use the existing builder only when an artifact is part of the requested delivery.
- Check the proposed name locally and remotely. Preserve published targets. An identical existing Tag can be reported as present; a conflicting target requires a new decision instead of moving the published Tag.
- Create the supported Tag at the exact accepted commit and read back its target. Push only the selected branch and this Tag using explicit source:destination refs. Disable automatic following of other Tags for this push, preserve hooks and avoid broad `--tags`, `--mirror` or force pushes. Use an atomic push when both refs must succeed together and the server supports it; otherwise verify each stage before retrying.
- Read back exact remote refs and compare their commit targets. An annotated Tag's object ID differs from its peeled commit ID; verify the latter. Cached tracking refs and a successful exit alone do not establish the remote target.

For a resolved remote, branch, Tag and commit, an explicit atomic push can use `git -c push.followTags=false push --atomic <remote> <commit>:refs/heads/<branch> refs/tags/<tag>:refs/tags/<tag>`. Read back with `git ls-remote <remote> refs/heads/<branch> refs/tags/<tag> 'refs/tags/<tag>^{}'`. Resolve placeholders, shell quoting and Git support before use; these examples are not execution authorization.

Report commit/push, local Tag, remote Tag, CI and Release separately. A Tag does not establish artifact integrity, installation or client reload. Update only authorized installations through their existing source after delivery.

## Sources

[Git Tagging](https://git-scm.com/book/en/v2/Git-Basics-Tagging), [Git push](https://git-scm.com/docs/git-push) and [Semantic Versioning](https://semver.org/spec/v2.0.0.html), checked 2026-10-09
