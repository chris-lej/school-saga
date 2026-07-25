# Autonomy v2 guarded production GitHub transport

The production mutation transport is isolated from Worker, Reviewer, Merger, scheduler, and policy code. It remains unavailable unless `production_guarded` mode and a complete readiness manifest are supplied.

## Required controls

Every command is checked against:

- repository allowlist;
- permitted mutation-kind allowlist;
- explicit review enablement;
- explicit merge enablement;
- stable operation ID;
- required expected-head metadata for reviews and merges.

Dry-run execution remains the default path.

## Supported mutation kinds

- claim issue;
- create branch;
- open pull request;
- submit review;
- merge pull request.

Review and merge capabilities are separately disabled by default. Enabling issue, branch, and pull-request mutations does not implicitly enable reviews or merges.

## Idempotency and audit

Before invoking the client, the transport checks persisted operation results. A repeated operation ID returns the stored result without issuing a second remote mutation.

Successful operations persist:

- operation ID;
- mutation kind;
- repository;
- normalized remote result;
- a structured `github.mutation.executed` audit event.

## Failure handling

The transport normalizes failures into `GitHubAdapterError` classifications:

- permission;
- not found;
- conflict or stale input;
- transient/retryable infrastructure failure;
- invalid response.

Production callers must not silently retry terminal failures. Scheduler retry policy remains bounded.

## Secrets and permissions

Credentials are not stored in this repository. A concrete client must load its token from the readiness manifest's declared secret source and use the narrowest practical permissions.

Review and merge tokens or permissions should be independently revocable. The emergency stop and rollback procedure must be controlled outside the agent process.

## Remaining boundary

This slice does not:

- generate or edit code;
- install a live GitHub client;
- deploy an always-on scheduler;
- enable production review or merge by default;
- alter the Godot runtime.

## Validation

```bash
python -m unittest discover -s tests/autonomy -p 'test_*.py'
bash scripts/validate-pr.sh
```
