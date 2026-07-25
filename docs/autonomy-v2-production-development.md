# Autonomy v2 guarded production development

This activation slice permits the autonomous development system to create validated commits and draft pull requests for `chris-lej/school-saga`. It does not authorize automated review, approval, readiness transitions, or merge.

## Activation boundary

Production development remains disabled unless all of the following are explicitly configured:

- `production_development_guarded` activation;
- repository identity exactly matching `chris-lej/school-saga`;
- complete production-readiness manifest;
- repository allowlist entry;
- mutation permission for issue claim, branch creation, and pull-request creation;
- trusted token and emergency-stop sources;
- a valid local repository root;
- draft-pull-request-only policy;
- disabled production review and merge capabilities.

The activation runner is one-shot. This issue does not deploy an always-on scheduler.

## Allowed outcome

A successful run may:

1. operate on an eligible persisted job;
2. apply an allowlisted bounded code-edit plan;
3. create a real local Git commit;
4. pass the configured validation service;
5. create the guarded remote branch operation;
6. open a draft pull request;
7. persist the complete result and audit trail.

The resulting pull request must remain draft. A human is responsible for review, marking it ready, and merging.

## Preflight gates

The production runner checks:

- activation is enabled;
- exact repository identity;
- eligible job lifecycle state;
- deterministic branch prefix;
- draft-only policy;
- review remains disabled;
- merge remains disabled;
- emergency stop is inactive.

The Worker and transport retain their repository, path, patch-size, changed-file, attempt, expected-base, expected-head, validation, and idempotency guards.

## Restart behavior

The production report is stored under a stable operation ID. Repeating a completed invocation returns the persisted report instead of repeating the Worker or remote mutations.

Worker workspace, validation, branch, and pull-request operations retain their own stable IDs. A restart must not create a second commit, branch, or pull request.

## Required token permissions

Use the narrowest token capable of:

- reading repository and issue metadata;
- updating or claiming eligible issues;
- creating branches;
- creating draft pull requests.

Do not grant merge permission for this activation stage. Review and merge credentials should remain independently disabled or unavailable.

## Emergency stop

The emergency-stop source must be externally controlled and independently revocable. When active, the runner persists a halted report before invoking the Worker.

Operators should test the stop before production activation and after any credential or deployment change.

## Rollback and incident response

1. Activate the emergency stop.
2. Stop all production-development runner processes.
3. Revoke or rotate the mutation token.
4. Inspect persisted operation and audit records.
5. Inspect the local workspace and remote draft PR.
6. Close the draft PR if it should not proceed.
7. Delete the remote and local issue branch only after preserving required evidence.
8. Correct configuration or code before reactivation.

Never force push or rewrite history during recovery.

## Activation checklist

- [ ] PR implementing this mode has passed all repository validation.
- [ ] Repository, path, command, mutation, file-count, patch-size, and attempt allowlists are reviewed.
- [ ] Required checks match current branch protection.
- [ ] Token scope and secret source are reviewed.
- [ ] Emergency stop has been exercised.
- [ ] Rollback and incident ownership are assigned.
- [ ] First production issue is narrow and reversible.
- [ ] Operator will inspect every initial draft PR.
- [ ] Automated review and merge remain disabled.

## Validation

```bash
python -m unittest discover -s tests/autonomy -p 'test_*.py'
bash scripts/validate-pr.sh
```
