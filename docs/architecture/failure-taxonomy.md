# Failure Taxonomy

Every failed stage must be classified into exactly one primary category. Classification determines ownership and the permitted next action.

## Categories

### `implementation`

The implementation agent could not produce a coherent change or produced no committable work.

Owner: Implementer or Supervisor.

Typical action: block or request a clean retry. Do not treat the absence of host tools as an implementation failure.

### `validation-code`

Objective validation ran successfully and found a defect attributable to repository changes.

Owner: Repairer, within a bounded repair budget.

Typical action: produce a repair attempt, rerun validation, and retain the issue in `state:implementing`.

### `review`

The Reviewer found correctness, maintainability, architecture, or project-conformance problems.

Owner: Repairer or Implementer according to policy.

Typical action: address specific review findings and request another review. Reviewer findings must not include CI status, deployment status, or mergeability.

### `environment`

The configured host cannot execute a required stage because a local prerequisite is missing or invalid.

Examples: missing Godot executable, unsupported runtime version, missing shell, unavailable filesystem capability.

Owner: Operator or platform administrator.

Typical action: transition to `state:blocked`. Never dispatch code repair.

### `infrastructure`

An external service or platform dependency is unavailable or malfunctioning.

Examples: GitHub outage, network failure, rate limiting, unavailable runner, corrupted external cache.

Owner: Operator or platform administrator.

Typical action: preserve durable state, retry orchestration according to infrastructure policy, or block after the budget is exhausted. Never ask an implementation agent to change code solely to fix infrastructure.

### `policy`

A required organizational rule prevents continuation.

Examples: repair budget exhausted, required artifact missing, prohibited transition, approval policy unmet.

Owner: Supervisor or Human.

Typical action: block with the violated rule and required decision.

### `merge`

Publication cannot proceed because a merger-owned gate failed.

Examples: required CI has not passed, branch protection is unmet, merge conflict exists, approval is missing.

Owner: Merger or Human.

Typical action: wait, repair the conflict through an authorized path, or block. The Reviewer does not own this classification.

### `human-required`

Intent, scope, risk, or authorization cannot be resolved automatically.

Owner: Human.

Typical action: transition to `state:blocked` with one concrete question or required action.

## Classification rules

1. Classify the immediate cause, not the most visible symptom.
2. Missing executables and credentials are environment failures even when discovered during validation.
3. A test assertion caused by changed code is `validation-code`.
4. A test runner that cannot start because the host is misconfigured is `environment`.
5. A GitHub API timeout is `infrastructure`, not `implementation`.
6. Required CI status is evaluated only by the Merger.
7. Every failure artifact must include category, stage, summary, evidence, owner, retryability, and next action.
