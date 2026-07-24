# Autonomy v2 Worker dry-run lifecycle

The first Worker v2 slice is deliberately limited to deterministic planning, lifecycle ownership, dry-run GitHub intent, and shared validation.

## State ownership

The Worker owns these states:

- `queued`
- `claimed`
- `executing`
- `validating`

It refuses to operate in Reviewer-, Merger-, or terminal states.

A normal dry-run proceeds as follows:

```text
queued -> claimed -> executing -> validating
```

Every transition uses a stable operation ID derived from the job ID. Re-running the Worker after a process restart therefore resumes instead of duplicating lifecycle events.

## Eligibility

A fixture issue is eligible when it is:

- open;
- labeled `state:ready`.

Ineligible work is transitioned to `blocked` with a typed error and a structured `worker.blocked` audit event.

## Work planning

The Worker creates a typed `WorkPlan` containing:

- issue number and title;
- unchecked acceptance-criteria items parsed from the issue body;
- deterministic branch intent;
- a dry-run summary.

The plan is persisted as an idempotent operation result and a `worker.plan.created` audit event.

This slice does not generate code, edit repository files, or invoke a model. Issue text is treated as planning input only; executable commands continue to come from trusted repository configuration.

## GitHub safety boundary

The Worker emits mutation command intent for:

- issue claim;
- branch creation;
- pull-request creation.

Those commands are sent only to `DryRunMutationExecutor`. No GitHub mutation transport is configured, and no production write is performed.

## Validation

The Worker transitions to `validating` and invokes the shared `ValidationService`. The resulting operation ID and status are linked into the persisted Worker result.

Repeating the Worker run reuses the persisted validation result and does not rerun commands unless a future caller explicitly chooses a distinct validation operation ID.

## Current limitations

This is not yet an autonomous coding Worker. It does not:

- create commits;
- modify source files;
- open a real pull request;
- start a background loop;
- invoke Reviewer or Merger;
- enable autonomous merge.

Those capabilities require separate implementation and safety reviews.

## Validation

```bash
python -m unittest discover -s tests/autonomy -p 'test_*.py'
bash scripts/validate-pr.sh
```
