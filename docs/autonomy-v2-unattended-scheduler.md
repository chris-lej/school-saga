# Autonomy v2 bounded unattended scheduler

This deployment layer repeatedly invokes the guarded production lifecycle only after readiness verification and lease acquisition.

## Deployment modes

- `disabled`: refuses to start.
- `observe_only`: verifies readiness and scheduler ownership without executing production work.
- `single_cycle`: runs at most one guarded production cycle.
- `always_on`: runs a bounded number of cycles per process invocation and may be restarted by an external service manager.

Always-on mode does not weaken the Worker, Reviewer, Merger, expected-head, validation, quarantine, or emergency-stop policies.

## Startup requirements

Before starting:

1. verify a current signed READY report against the exact `main` SHA and configuration digest;
2. confirm the emergency stop is reachable and inactive;
3. acquire the single scheduler lease;
4. confirm one-active-issue policy;
5. confirm audit persistence is writable;
6. begin in observe-only mode, then single-cycle mode, before promoting to always-on.

Startup fails closed when readiness verification, lease acquisition, or safety configuration fails.

## Runtime controls

Operators can:

- pause before the next cycle;
- resume a paused scheduler;
- drain after the current completed cycle;
- request graceful shutdown;
- activate the emergency stop before the next mutation.

The scheduler heartbeats its lease before each cycle and releases the lease on exit.

## Health evidence

Each run reports:

- scheduler state;
- readiness report reference;
- last successful cycle;
- failed-cycle count;
- quarantined issue numbers;
- per-cycle status, issue number, detail, and operation IDs.

External monitoring should alert on stale heartbeats, repeated failed cycles, stale readiness, a growing quarantine set, or an active emergency stop.

## Recovery and rollback

On an incident:

1. activate the emergency stop;
2. pause or shut down the scheduler;
3. revoke or rotate the GitHub token when remote state is uncertain;
4. preserve readiness, scheduler, job, operation, review, and merge records;
5. verify the exact current `main` SHA and configuration digest;
6. quarantine unsafe issues rather than retrying blindly;
7. require a new READY report before resuming;
8. restart first in observe-only mode.

The scheduler never force-pushes, rewrites history, or writes directly to `main`.

## Promotion criteria

Enable always-on mode only after several successful supervised canaries and single-cycle runs demonstrate:

- correct patch scope and validation;
- dependable Reviewer findings and Worker fixes;
- exact-head approval and merge enforcement;
- restart idempotency;
- effective emergency stop;
- complete audit linkage;
- poison-issue quarantine without queue blockage.

Concurrency above one active issue requires a separate design and approval.

## Validation

```bash
python -m unittest discover -s tests/autonomy -p 'test_*.py'
bash scripts/validate-pr.sh
```
