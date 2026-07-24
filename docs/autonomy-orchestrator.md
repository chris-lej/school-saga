# Autonomy v2 dry-run orchestrator

The orchestrator coordinates existing stateless agents by reading the persisted job state and dispatching exactly one owning agent. It does not duplicate Worker, Reviewer, or Merger policy.

## Dispatch ownership

- `queued`, `claimed`, `executing` -> Worker
- `validating`, `reviewing` -> Reviewer
- `approved`, `merging` -> Merger
- `blocked`, `failed`, `cancelled`, `completed` -> terminal, no agent

Reviewer and Merger dispatch require an explicit pull-request number. Missing linkage fails safely with `OrchestratorError`.

## Persistence and restart recovery

Each state-specific dispatch uses a stable operation ID:

```text
<job_id>:orchestrator:dispatch:<state>
```

The dispatch result and a structured `orchestrator.dispatched` event are persisted. Repeating the same operation returns the stored result instead of executing an agent twice.

Because the agents themselves read all required state and artifacts from `JsonJobStore`, restarting between stages resumes from the current persisted lifecycle state.

## Operating modes

`dispatch_once` performs one state-derived action.

`run_to_terminal` repeatedly dispatches with a bounded maximum number of steps. It stops on terminal state and fails if an agent makes no lifecycle progress or the dispatch bound is exceeded.

This slice intentionally does not provide an always-on daemon, polling scheduler, or automatic retry loop.

## Safety boundary

- Dry-run Worker, Reviewer, and Merger only.
- No production GitHub mutations, reviews, or merges.
- No code generation or repository editing.
- No hidden supervisor state.
- No unbounded retries.

## Validation

```bash
python -m unittest discover -s tests/autonomy -p 'test_*.py'
bash scripts/validate-pr.sh
```
