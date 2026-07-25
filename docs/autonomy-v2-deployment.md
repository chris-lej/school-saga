# Autonomy v2 production deployment

This package is the operator-facing boundary for launching the guarded autonomous-development stack.

## Launch sequence

1. Update the local checkout and record the exact `main` SHA.
2. Confirm the worktree is clean and all required checks are visible.
3. Verify the GitHub token scopes, signing-key source, emergency stop, audit store, and scheduler lease store.
4. Generate and verify a current signed READY report.
5. Run the deployment command in `readiness` mode.
6. Run `observe` mode and inspect the persisted deployment state.
7. Run `single_cycle` for one small canary issue.
8. Inspect the branch, commit, validation, PR, review, merge, scheduler record, and audit trail.
9. Enable `always_on` only after successful supervised evidence.

The configuration remains disabled by default. Observe-only is the default deployment mode.

## Configuration boundary

Trusted configuration must define:

- exact repository identity and local root;
- expected `main` SHA;
- path, command, and mutation allowlists;
- required checks;
- token and signing-key sources;
- emergency-stop source;
- audit-store and state-store paths;
- exclusive scheduler lease owner;
- bounded cycle count and retry backoff;
- explicit deployment enablement.

Configuration is loaded from trusted operator-controlled JSON. Issue text is never interpreted as configuration, code, or commands.

## Operator commands

- `readiness`: verify startup prerequisites without starting the scheduler.
- `observe`: acquire safety context and scheduler ownership without production work.
- `single_cycle`: execute at most one guarded issue lifecycle.
- `always_on`: execute a bounded number of cycles per process invocation.
- `pause`: stop before the next cycle.
- `resume`: clear pause and drain state.
- `drain`: stop after the current completed cycle.
- `status`: read persisted deployment state.
- `shutdown`: request graceful shutdown.

An external service manager may restart bounded always-on invocations, but must not bypass readiness, emergency-stop, lease, or one-active-issue controls.

## Persisted state

The deployment state records:

- readiness report reference;
- scheduler state;
- active issue;
- last successful cycle;
- failed-cycle count;
- quarantined issues;
- cumulative cycle count.

Writes use a temporary file and atomic replacement to preserve restart recovery.

## Health and monitoring

Alert on:

- stale readiness or changed `main`;
- failed lease acquisition or stale heartbeat;
- repeated failed cycles;
- growing quarantine count;
- active emergency stop;
- missing audit records;
- a scheduler process that exits unexpectedly.

## Rollback and incident response

1. Activate the emergency stop.
2. Pause, drain, or shut down the scheduler.
3. Revoke or rotate the GitHub token when remote state is uncertain.
4. Preserve readiness, deployment, scheduler, job, review, merge, and audit records.
5. Compare the current repository SHA and configuration digest against the readiness report.
6. Quarantine unsafe issues and branches rather than retrying blindly.
7. Require a new signed READY report.
8. Restart in observe-only mode before any production cycle.

The deployment never force-pushes, rewrites history, executes issue text, or writes directly to `main`.

## Validation

```bash
python -m unittest discover -s tests/autonomy -p 'test_*.py'
bash scripts/validate-pr.sh
```
