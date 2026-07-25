# Autonomy v2 guarded rehearsal

The guarded rehearsal exercises the issue-to-draft-PR boundary in an explicitly isolated repository. It is a promotion test, not production activation.

## Preconditions

- The repository must be present in a dedicated rehearsal allowlist.
- The persisted job must be in `claimed`, `executing`, or `validating`.
- The guarded code-editing Worker must be explicitly enabled.
- The Worker must use bounded path, patch-size, file-count, validation, and draft-PR policies.
- Production review and merge capabilities must remain disabled.
- An externally controlled emergency-stop source must be available.

Automated tests must never target `chris-lej/school-saga` for remote mutations.

## Execution boundary

`GuardedRehearsalRunner.run_to_draft_pr` delegates the actual workspace, validation, branch, and draft-PR work to the guarded Worker. It adds:

- isolated-repository enforcement;
- emergency-stop checks;
- a persisted machine-readable rehearsal report;
- stable restart idempotency;
- explicit unresolved production gates.

A successful report has status `draft_pr_created` and records the local commit SHA and pull-request number.

## Report gates

The report records whether these gates passed:

- isolated repository allowlisted;
- draft-pull-request-only policy active;
- production review disabled;
- production merge disabled;
- repository validation passed;
- real local commit created;
- draft pull request created.

It also retains unresolved production gates. A successful rehearsal does not authorize production review, merge, or an always-on scheduler.

## Emergency stop and recovery

When the emergency stop is active, the runner persists `rehearsal.halted` and performs no Worker action. Existing job, workspace, and remote-operation state remain available for inspection and explicit recovery.

Repeating a completed rehearsal returns its persisted report and does not repeat the Worker or remote mutations.

## Promotion criteria

Before proposing activation against the game repository, require human review of:

1. the complete rehearsal report and audit trail;
2. repository, mutation, path, and command allowlists;
3. token scopes and secret source;
4. rollback and branch-cleanup procedure;
5. emergency-stop ownership and test evidence;
6. required checks and expected-head protections;
7. continued independent Reviewer and Merger gates.

Production review and merge activation must remain separate changes.

## Validation

```bash
python -m unittest discover -s tests/autonomy -p 'test_*.py'
bash scripts/validate-pr.sh
```
