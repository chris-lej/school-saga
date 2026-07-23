# Recovery and Human Intervention

## Recovery objectives

The platform must survive process termination, host restart, transient GitHub failures, and partially completed stages without duplicating externally visible work or losing the evidence needed to continue safely.

## Durable checkpoints

The Supervisor records, at minimum:

- work-order number;
- run and attempt identifiers;
- canonical workflow state;
- current stage and producing role;
- branch and pull-request identity;
- latest artifact references;
- bounded retry counters;
- last classified failure.

A checkpoint is orchestration metadata. It is not an implementation artifact and must not be committed as project source.

## Recovery order

On startup, the Supervisor reconciles work in this order:

1. validate its own configuration and GitHub access;
2. reconcile any local durable checkpoint with GitHub and Git evidence;
3. reconcile issues already in active states;
4. resume eligible transient infrastructure retries;
5. consume explicit `state:retry` requests;
6. select new `state:ready` work.

The Supervisor never selects a second work order while unresolved active work exists for a single-worker deployment.

## Idempotency requirements

- Branch creation is reconciled before creation.
- Pull-request creation checks for an existing PR from the implementation branch.
- Artifact publication uses immutable attempt identifiers.
- State transitions compare the current canonical state before mutation.
- Merge checks the expected head commit and records the result.
- Comments include run identifiers so duplicate projections can be detected.

## Automated retry

Automated retry is permitted only when the failure taxonomy and policy explicitly allow it.

- Code-caused validation failures may dispatch the Repairer within a bounded budget.
- Review findings may dispatch the Repairer within a bounded budget.
- Transient infrastructure operations may be retried with backoff.
- Environment, policy, authorization, and human-required failures are not automatically retried.

Exhausting any retry budget produces a policy failure and moves the work order to `state:blocked`.

## Human intervention contract

A blocked work order must present one actionable intervention request containing:

- what failed;
- the classified category;
- why automation cannot continue;
- the owner of the next action;
- the exact action required;
- whether `state:retry` is appropriate afterward;
- references to artifacts and detailed logs.

Humans may change intent or authorize risk. Automated agents must not infer authorization from silence.

## Retry versus resume

- **Resume** continues the same run from durable evidence and preserves the branch and prior artifacts.
- **Repair** creates another bounded attempt against the same implementation branch in response to a specific finding.
- **Retry** is an operator-controlled clean start. It discards execution checkpoints and supersedes the previous implementation attempt.

These operations must never be conflated.

## Abandonment

`state:abandoned` is terminal and indicates that the work order should not continue. The Supervisor records the human-provided reason and stops all automated activity for the issue.

## Closed issues and external mutation

If an issue is closed, merged, relabeled, or otherwise changed outside the Supervisor, the next reconciliation cycle treats GitHub as authoritative. The Supervisor records the discrepancy, avoids destructive assumptions, and either adopts the valid external state or blocks for clarification when the external mutation is ambiguous.
