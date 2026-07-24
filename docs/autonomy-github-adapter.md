# Autonomy v2 GitHub adapter

The GitHub adapter isolates remote repository access from Worker, Reviewer, and Merger policy.

## Default operating mode

The default mutation path is `DryRunMutationExecutor`.

Dry-run execution:

- does not call a GitHub mutation transport;
- emits a structured `github.mutation.dry_run` audit event;
- records the intended repository and payload;
- returns the same result when the same operation ID is repeated.

`GuardedMutationExecutor` fails closed unless both conditions are true:

1. `mutations_enabled=True` is explicitly supplied;
2. an explicit mutation transport is provided.

No agent loop is started by this module.

## Read contracts

`GitHubAdapter` maps transport responses into deterministic snapshots for:

- repository metadata;
- issues and labels;
- pull requests and head revisions;
- combined check state.

Malformed responses raise `GitHubAdapterError` with `INVALID_RESPONSE` rather than silently coercing missing data.

## Mutation commands

Mutation intent is represented by `MutationCommand` with a stable operation ID and one of these kinds:

- `claim_issue`
- `create_branch`
- `open_pull_request`
- `submit_review`
- `merge_pull_request`

Commands are policy-neutral. Agent implementations decide when a command is appropriate; an executor decides whether it may run.

## Credentials and permissions

Fixture tests and dry-run mode require no credentials.

A future production transport should use the narrowest practical GitHub token permissions. Read operations need repository metadata, issues, pull requests, and checks. Mutation permissions must be enabled only for the specific operations being deployed. Secrets must be supplied through the runtime environment or secret manager and must never be committed.

Autonomous merge remains disabled until a separate production-readiness review is completed.

## Validation

```bash
python -m unittest discover -s tests/autonomy -p 'test_*.py'
bash scripts/validate-pr.sh
```
