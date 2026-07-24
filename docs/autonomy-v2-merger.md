# Autonomy v2 Merger dry-run lifecycle

The first Merger v2 slice evaluates persisted Reviewer and validation evidence against deterministic merge policy. It performs no production GitHub merge.

## State ownership

The Merger owns:

- `approved`
- `merging`
- `completed`

A successful dry-run moves through:

```text
approved -> merging -> completed
```

Worker-, Reviewer-, and terminal states are rejected.

## Required artifacts

The Merger consumes:

- `<job_id>:reviewer:result`
- `<job_id>:worker:validation`

Missing artifacts fail with `MergerError` rather than being inferred.

## Policy

A merge decision is allowed only when:

- the persisted review is approved;
- the reviewed head SHA matches the current pull-request head;
- persisted validation passed;
- the pull request is open and not a draft;
- the pull request targets the configured default branch;
- required checks are successful.

Every failed condition becomes a typed blocking `MergeFinding`.

## Expected-head protection

The dry-run merge command includes the current pull-request head SHA as `expected_head_sha`. A future production transport must preserve this guard so a moved head cannot be merged using stale approval evidence.

## Persistence and idempotency

The Merger persists:

- a typed merge report;
- the merge decision;
- expected head SHA and merge-method intent;
- structured audit events;
- a final dry-run result.

Stable operation IDs prevent duplicate transitions, decisions, and events during restart or retry.

## Safety boundary

Merge intent is sent only to `DryRunMutationExecutor`. No GitHub merge transport is enabled, and autonomous merge remains disabled.

This slice does not generate code, modify repository files, or start a background orchestration loop.

## Validation

```bash
python -m unittest discover -s tests/autonomy -p 'test_*.py'
bash scripts/validate-pr.sh
```
