# Autonomy v2 validation service

The validation service provides a shared, deterministic repository gate for future Worker and Reviewer agents.

## Commands

Validation commands are configured by trusted repository code. They must not be created from issue body text or other untrusted input.

The initial School Saga command group is:

```bash
python -m unittest discover -s tests/autonomy -p 'test_*.py'
bash scripts/validate-pr.sh
```

`ValidationService` executes commands in order and stops after the first non-passing step.

## Statuses

Each step and aggregate run uses one of these statuses:

- `passed`
- `failed`
- `timed_out`
- `unavailable`
- `infrastructure_error`

A run passes only when every configured step passes.

## Safety boundary

The local subprocess runner:

- uses an explicit working directory;
- receives only allowlisted environment variables;
- captures bounded stdout and stderr;
- applies a timeout to every command;
- does not perform GitHub mutations;
- does not start Worker, Reviewer, or Merger loops.

Secrets must never be included in configured commands or persisted output.

## Idempotency and retries

A validation operation is keyed by `operation_id`. Repeating the same operation returns the persisted result and does not rerun commands or duplicate audit events.

A retry must use a new operation ID. This creates a new validation attempt and increments attempt metadata.

## Audit trail

Completed runs emit a `validation.completed` audit event containing:

- operation ID;
- attempt number;
- aggregate status;
- ordered step results;
- bounded command output.

## Local tests

```bash
python -m unittest discover -s tests/autonomy -p 'test_*.py'
bash scripts/validate-pr.sh
```

Autonomous merge remains disabled until a later production-readiness review.
