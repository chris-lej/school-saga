# Autonomy v2 supervised production activation

This entrypoint authorizes one operator-selected production issue only after a signed readiness report verifies against the exact repository SHA and trusted configuration.

## Operating modes

### Dry-run preflight

Dry-run mode verifies:

- the readiness report signature, expiry, repository identity, SHA, and configuration digest;
- that the emergency stop is inactive;
- that no other production job is active;
- that exactly one issue was selected.

It performs no production runtime action.

### Supervised live canary

Live mode additionally requires explicit confirmation. It invokes the composed production runtime for exactly one selected issue and records the resulting operation identifiers and lifecycle result.

The runtime is responsible for composing the real job store, Git workspace, validation service, guarded GitHub transport, Worker, Reviewer, Merger, queue adapter, and production loop.

## Safety boundary

- Disabled by default.
- One selected issue per invocation.
- One active production job.
- Signed readiness must still be valid for the exact current `main` SHA and configuration.
- Emergency stop is checked before readiness verification and immediately before production runtime execution.
- Live execution requires a separate confirmation flag.
- No force push, history rewrite, direct writes to `main`, or execution of issue text.
- Always-on scheduling remains disabled.

## Canary procedure

1. Update the local checkout and record the exact `main` SHA.
2. Confirm a clean worktree and required checks.
3. Verify token scopes and emergency-stop ownership.
4. Generate and inspect a signed READY report.
5. Run the activation command in dry-run mode for one small `state:ready` issue.
6. Confirm no other production job is active.
7. Re-run with explicit live confirmation.
8. Inspect every operation identifier, branch, commit, PR, review decision, validation result, and merge result.
9. Stop after the single issue and review the audit trail.

## Failure and rollback

On any halt, mismatch, or unexpected mutation:

1. activate the emergency stop;
2. revoke or rotate the GitHub token;
3. preserve the readiness report, activation report, job store, and audit events;
4. compare current `main` and configuration against the readiness binding;
5. quarantine the selected issue and branch when state is uncertain;
6. remove an unneeded branch only after preserving its commit and audit evidence;
7. require a new readiness report before retrying.

## Promotion criteria

Before enabling bounded multi-issue or unattended operation, require several successful supervised canaries with evidence of:

- correct patch scope and validation;
- exact-head review and merge protection;
- restart idempotency;
- emergency-stop effectiveness;
- complete audit linkage;
- correct quarantine and recovery behavior.

Always-on scheduling requires a separate approval and implementation slice.

## Validation

```bash
python -m unittest discover -s tests/autonomy -p 'test_*.py'
bash scripts/validate-pr.sh
```
