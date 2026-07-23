# Workflow State Machine

## Canonical lifecycle labels

Exactly one canonical state label may be present on an open work-order issue:

- `state:ready`
- `state:implementing`
- `state:review`
- `state:merge`
- `state:done`
- `state:blocked`
- `state:retry`
- `state:abandoned`

Auxiliary labels may describe priority, role, or diagnostics, but they must not compete with the canonical state.

## Normal flow

```text
state:ready
  -> state:implementing
  -> state:review
  -> state:merge
  -> state:done
```

## Exception flow

```text
any active state -> state:blocked
state:blocked -> state:retry
state:retry -> state:ready
any nonterminal state -> state:abandoned
```

## Ownership

| State | Owner | Required output |
|---|---|---|
| `state:ready` | Supervisor | selected context package and dispatch decision |
| `state:implementing` | Implementer | repository changes and implementation artifact |
| `state:review` | Reviewer | review artifact |
| `state:merge` | Merger | merge artifact and merge decision |
| `state:done` | Supervisor | terminal run summary |
| `state:blocked` | Supervisor/Human | blocker summary and required operator action |
| `state:retry` | Human/Supervisor | clean-slate reset decision |
| `state:abandoned` | Human | terminal cancellation reason |

Validation is an objective gate between implementation and review. It does not own a persistent issue state in Version 1; its result is recorded as a validation artifact while the issue remains `state:implementing`. A successful validation result allows transition to `state:review`. A code-caused validation failure may dispatch the Repairer. An environment or infrastructure failure transitions to `state:blocked`.

## Transition rules

1. The Supervisor is the only component allowed to mutate canonical workflow labels, except explicit human overrides.
2. A state transition must remove every other canonical state label before adding the target state.
3. Every transition must be justified by durable evidence: an artifact, a GitHub event, or an operator action.
4. Retrying is never implicit. `state:retry` means discard prior execution state and start from the latest base branch.
5. Repair attempts do not reset the work order. They remain inside `state:implementing` and are bounded by policy.
6. `state:done` and `state:abandoned` are terminal.

## Clean retry semantics

When the Supervisor consumes `state:retry`, it must:

1. record the retry request and reason;
2. clear local checkpoints;
3. remove or archive stale generated artifacts;
4. delete or supersede the prior implementation branch when safe;
5. reset the workspace to the latest configured base branch;
6. transition the issue to `state:ready`;
7. allow a future cycle to create a new context package and implementation attempt.

Reset and reimplementation are separate durable operations so a crash cannot leave the issue falsely marked as implementing.

## Illegal examples

- Reviewer changes `state:review` to `state:merge` directly.
- Implementer marks its own work `state:done`.
- Validator changes workflow labels.
- CI failure adds an ad hoc `ci:failed` lifecycle label.
- Supervisor retries a blocked issue without `state:retry` or an equivalent explicit operator action.
