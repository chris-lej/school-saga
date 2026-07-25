# Autonomy v2 guarded production development

This activation slice permits operator-triggered development against `chris-lej/school-saga` through validated real commits and draft pull requests. It does not authorize automated review, readiness transitions, merge, auto-merge, force-push, deletion, or unattended scheduling.

## Activation boundary

Production development remains disabled unless a complete `ProductionDevelopmentConfig` is supplied in `production_guarded` mode. Initial activation is limited to one active job and one operator-triggered cycle.

Required controls:

- production repository allowlist;
- permitted mutation allowlist limited to issue claim, branch creation, and draft-PR creation;
- path and validation-command allowlists;
- required checks;
- explicit token source;
- rollback procedure;
- emergency-stop source;
- draft-pull-request-only policy;
- review, merge, and always-on scheduling disabled.

## One-shot operating sequence

1. Confirm the emergency stop is inactive and independently controlled.
2. Confirm the selected issue is eligible and labeled `state:ready`.
3. Verify the expected base SHA and a clean isolated local worktree.
4. Run one production-development cycle.
5. Inspect the machine-readable activation report, validation output, commit SHA, branch, and draft PR.
6. Leave the PR in draft for human review.
7. Disable the activation mode after the cycle.

## Fail-closed conditions

Activation stops on incomplete readiness configuration, repository mismatch, forbidden mutation capability, stale base/head/ref, dirty workspace, failed validation, path or command allowlist mismatch, active emergency stop, or an ineligible job state.

Repeated cycles use persisted operation and report identifiers and must not duplicate remote mutations or commits.

## Rollback

Before any merge:

- activate the emergency stop;
- disable production-development mode;
- revoke or rotate the mutation token when compromise is suspected;
- close the draft PR if it should not proceed;
- delete the issue branch only after confirming no work must be retained;
- preserve the activation report and audit trail for diagnosis.

No force push or history rewrite is part of the recovery procedure.

## Promotion criteria

Automated Reviewer capability may only be proposed after several successful draft-PR cycles have been inspected by a human. Merge and auto-merge remain separate, later decisions. An always-on scheduler also requires a separate deployment and operations review.

## Validation

```bash
python -m unittest discover -s tests/autonomy -p 'test_*.py'
bash scripts/validate-pr.sh
```
