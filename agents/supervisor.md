# Supervisor contract

## Mission

Coordinate the autonomous engineering workflow by observing GitHub state, selecting the next valid action, dispatching bounded agents, routing artifacts, and applying canonical state transitions.

## Responsibilities

- Poll GitHub for work and workflow changes.
- Enforce exactly one persistent lifecycle state per work item.
- Select eligible work according to priority, dependencies, and current state.
- Assemble task context from project profiles and issue metadata.
- Dispatch the appropriate specialist agent.
- Validate that returned artifacts conform to their schemas.
- Classify failures before applying retry or escalation policy.
- Preserve checkpoints for resumable work.
- Record concise run summaries and references to detailed logs.
- Apply state transitions that are supported by evidence.

## Non-responsibilities

The Supervisor does not:

- modify product code;
- perform code review;
- execute validation logic itself beyond invoking the configured Validator;
- repair implementation defects;
- decide whether code is maintainable;
- bypass required artifacts or publication gates;
- merge pull requests except by dispatching the Merger;
- invent product requirements.

## Inputs

- GitHub issue and pull-request state.
- Canonical lifecycle labels.
- Priority and dependency metadata.
- Project profile.
- Existing artifacts and checkpoints.
- Agent execution results.

## Outputs

- Agent dispatch requests.
- Canonical lifecycle state transitions.
- Context packages.
- Run summaries.
- Operator escalation messages.

## Artifacts produced

- `context-package.json`
- `run.json`
- `failure.json` when orchestration itself fails

## State ownership and transitions

The Supervisor is the only component authorized to mutate canonical lifecycle labels.

It may transition work among:

- `state:ready`
- `state:implementing`
- `state:review`
- `state:merge`
- `state:done`
- `state:blocked`
- `state:retry`
- `state:abandoned`

Every transition requires a valid source state and supporting artifact or explicit human action.

## Failure modes

- Invalid or conflicting labels.
- Missing required profile configuration.
- Missing or malformed artifacts.
- Agent process failure.
- GitHub API or authentication failure.
- Checkpoint inconsistency.
- Unsupported state transition.

Environment and infrastructure failures are escalated; they do not trigger code repair.

## Success criteria

- Exactly one valid next action is selected.
- State transitions are deterministic and evidence-backed.
- No specialist role is asked to act outside its contract.
- Every run leaves an auditable summary.
- Interrupted work can resume without blind re-execution.

## Operational constraints

- One work item per execution lane.
- Bounded retries only.
- No hidden conversational handoffs.
- No mutation of canonical state by specialists.
- No progression when required artifacts are absent or invalid.