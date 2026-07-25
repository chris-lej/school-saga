# Autonomy v2 guarded production Worker

This activation slice permits one explicitly selected ready issue to reach a validated draft pull request in `chris-lej/school-saga`. It does not enable automated review, merge, or an unattended scheduler.

## Required manifest

The operator must supply a complete `ProductionWorkerManifest` containing:

- repository allowlist;
- path allowlist;
- validation command allowlist;
- remote mutation allowlist;
- required GitHub token scopes;
- draft-pull-request-only policy;
- disabled Reviewer, Merger, and always-on scheduler gates.

The manifest is validated before execution and its SHA-256 digest is persisted in the run report.

## Invocation boundary

`GuardedProductionWorkerRunner.run_selected_issue` accepts exactly one persisted job, one explicitly selected issue number, and one bounded `CodeEditPlan`.

Execution fails closed when:

- activation is not explicitly enabled;
- the emergency stop is active;
- repository or issue selection does not match the persisted job;
- the job is outside a Worker-owned state;
- the guarded Worker fails validation or does not create a draft pull request;
- any manifest gate is incomplete or unsafe.

The underlying guarded Worker retains base/head SHA protection, bounded path and patch policy, real local Git commit creation, stable operation IDs, and draft-PR-only remote mutation.

## Operator checklist

Before the first live invocation:

1. Review the complete production manifest and verify its digest.
2. Restrict the token to the minimum required repository and scopes.
3. Confirm branch protection and required checks on `main`.
4. Test the emergency stop immediately before the run.
5. Select exactly one small `state:ready` issue with narrow allowlisted paths.
6. Confirm Reviewer and Merger activation remain disabled.
7. Run interactively; do not use an always-on scheduler.
8. Inspect the resulting branch, commit, validation output, audit events, and draft PR before merging manually.

## Restart and recovery

Completed reports are stored under a stable operation ID. Repeating the same run returns the persisted report instead of invoking the Worker again.

If execution halts before completion, preserve the job store and local workspace. Do not reset or force-update the issue branch. Inspect persisted operation results and resolve stale base/head or branch movement before an explicit retry.

## Rollback and incident response

- Activate the emergency stop.
- Disable the production Worker enable flag.
- Revoke or rotate the GitHub token if remote mutation integrity is uncertain.
- Leave the draft PR unmerged while investigating.
- Compare the local commit, remote branch SHA, expected base/head SHA, and audit operations.
- Delete a remote issue branch only after confirming no work must be retained.
- Record the incident and require a fresh manifest review before reactivation.

## Remaining disabled gates

A successful production Worker run still reports:

- `production_reviewer_disabled`;
- `production_merger_disabled`;
- `always_on_scheduler_disabled`.

Those capabilities require separate implementation and explicit human approval.

## Validation

```bash
python -m unittest discover -s tests/autonomy -p 'test_*.py'
bash scripts/validate-pr.sh
```
