# Autonomy v2 Reviewer dry-run lifecycle

The first Reviewer v2 slice evaluates persisted Worker and validation artifacts against deterministic repository policy. It performs no production GitHub review or merge operation.

## State ownership

The Reviewer owns:

- `validating`
- `reviewing`
- `approved`

A successful review moves through:

```text
validating -> reviewing -> approved
```

The Reviewer refuses Worker-owned, Merger-owned, and terminal states.

## Required artifacts

The Reviewer consumes persisted operation results created by the Worker and validation service:

- `<job_id>:worker:result`
- `<job_id>:worker:validation`

Missing artifacts fail with an actionable `ReviewerError` rather than being inferred or silently recreated.

## Policy

Approval requires all of the following:

- persisted validation status is `passed`;
- the pull request is open;
- the pull request is not a draft;
- required checks are successful;
- when the Worker result includes a commit SHA, it matches the current pull-request head SHA.

Any failed condition produces a typed blocking finding. A non-approved review remains in `reviewing` so a later corrected run can be evaluated explicitly.

## Persistence and idempotency

The Reviewer persists:

- a typed review report;
- the reviewed head SHA;
- findings and approval status;
- a typed `ReviewResult`;
- structured audit events.

Stable operation IDs make repeated runs and process restarts idempotent. The same report, lifecycle transition, and audit event are not duplicated.

## GitHub safety boundary

Review intent is represented as a `submit_review` mutation command and sent only to `DryRunMutationExecutor`. No review is submitted to GitHub.

The payload records whether the intended event is `APPROVE` or `REQUEST_CHANGES` and pins the reviewed head SHA.

## Current limitations

This slice does not:

- inspect source-code diffs semantically;
- invoke a model;
- post a real GitHub review;
- modify repository files;
- merge pull requests;
- start a background orchestration loop.

Those capabilities require separate implementation and safety review.

## Validation

```bash
python -m unittest discover -s tests/autonomy -p 'test_*.py'
bash scripts/validate-pr.sh
```

Autonomous merge remains disabled.
