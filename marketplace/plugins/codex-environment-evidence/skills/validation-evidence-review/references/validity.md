# Evidence validity

The installed my-py-workspace-core 0.2.0 exposes validation.assess_evidence(recorded, current). Its CLI index accepts --current-baseline with an explicit JSON file; Workspace Inspection validation_evidence accepts the same current object. No recorded command is executed and no source/artifact path is opened by the comparison.

Provenance fields are source_revision, source_diff_sha256, source_files (relative input path to SHA-256), artifact_sha256 and covered_paths. Current input supplies the same actual observed identities plus affected_paths. Keep timestamps separately as observation time, not freshness proof. Include relevant untracked inputs in the supplied source digest/hash map; a tracked Git diff alone cannot describe them.

- current: supplied source identity or scoped input hashes match, any recorded artifact matches, and affected paths are covered
- outdated: a recorded input or artifact hash differs
- partial: source comparison matches but artifact/hash observations or affected-path coverage are incomplete
- unverified: no usable matching source identity, malformed old provenance or missing required context

A changed revision alone does not prove the tested behavior changed. Matching scoped input hashes can retain evidence for that scope; Main must still account for affected dependencies, runtime versions and acceptance behavior. A current source status does not turn a failed recorded test into PASS, prove all behavior or authorize skipping required checks.

Use existing run-*/results.json baseline objects, allowing per-result baseline overrides. Preserve legacy records as data. Do not create progress reports or read arbitrary files merely to populate this schema.
