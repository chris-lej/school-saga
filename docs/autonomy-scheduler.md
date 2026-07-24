# Autonomy v2 bounded scheduler

The bounded scheduler adds controlled recurring dispatch around the persisted dry-run orchestrator. It does not enable production GitHub mutations, code generation, or an always-on deployment.

## Operating modes

- `disabled`: no dispatch occurs.
- `dry_run`: eligible persisted jobs may be dispatched through the existing dry-run agents.
- `production_guarded`: initialization requires a complete production-readiness manifest, but this slice still does not install a production mutation transport.

The default configuration is `disabled`.

## Bounds

Every scheduler cycle applies explicit limits:

- maximum concurrent jobs;
- maximum dispatches per cycle;
- one lease per job;
- finite lease duration;
- finite retry backoff.

There is no unbounded polling or retry loop in this slice.

## Leases and restart recovery

A job lease records:

- job ID;
- lease ID;
- cycle ID;
- acquisition timestamp;
- expiration timestamp.

An unexpired lease prevents another scheduler instance from dispatching the same job. Expired leases are treated as recoverable after restart.

## Emergency stop

When `emergency_stop` is enabled, a scheduler cycle halts before acquiring leases or dispatching agents. Existing persisted jobs and artifacts are left unchanged.

A production deployment must source the emergency-stop setting from a separately controlled operational channel.

## Production-readiness manifest

`production_guarded` mode refuses to initialize unless the manifest includes:

- repository allowlist;
- permitted mutation kinds;
- required checks;
- merge policy;
- token source;
- rollback procedure;
- emergency-stop source.

This validates configuration completeness only. It does not enable real GitHub writes.

## Failure and backoff

A scheduler failure is persisted as `scheduler.dispatch.failed`. Retryable failures receive a persisted backoff record. Terminal configuration and data errors are surfaced without automatic retry.

## Current safety boundary

This scheduler only coordinates the existing dry-run Worker, Reviewer, and Merger. It does not:

- invoke a coding model;
- modify repository files;
- submit production GitHub reviews;
- merge pull requests;
- run as a daemon;
- install credentials or secret-management infrastructure.

## Validation

```bash
python -m unittest discover -s tests/autonomy -p 'test_*.py'
bash scripts/validate-pr.sh
```
