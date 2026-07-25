# Autonomy v2 real Git workspace backend

`GitWorkspaceBackend` replaces the synthetic commit boundary with an actual local Git commit while preserving the constrained code-editing contracts.

## Preconditions

The backend requires:

- an explicit local Git worktree;
- a clean working tree;
- an exact expected base SHA;
- an issue branch that is either absent or still points to the expected base;
- allowlisted repository paths;
- bounded changed-file and patch sizes.

It does not clone repositories, fetch remotes, push branches, or open pull requests by itself.

## Execution

The backend:

1. verifies the worktree and expected base SHA;
2. creates the deterministic issue branch, or resumes it only when it still points at the expected base;
3. applies the bounded file-change plan using the existing traversal, allowlist, and symlink protections;
4. refuses submodule entries;
5. stages only the declared paths;
6. verifies that the staged path set exactly matches the plan;
7. records the staged patch digest and tree SHA;
8. creates a real local commit and returns the actual commit SHA;
9. verifies the new commit has the expected base SHA as its parent.

The guarded Worker remains responsible for invoking the shared validation gate and for emitting guarded branch and draft-pull-request mutations.

## Recovery

Workspace and commit metadata are persisted by the Worker under stable operation IDs. After restart, the Worker reuses the persisted result instead of creating another commit.

A branch that moved away from the expected base is treated as a conflict. The backend does not force-reset or rewrite history.

## Rollback and cleanup

Before any remote push, rollback is local:

```bash
git checkout main
git branch -D autonomy/issue-<number>
```

Only perform deletion after confirming the branch has no work that must be retained. Production operations must keep the scheduler emergency stop active during recovery.

## Safety boundary

- Disabled unless the guarded Worker is explicitly enabled.
- No commands are sourced from issue text.
- No force push, history rewrite, review, or merge behavior.
- No live GitHub credentials are required by the integration tests.
- No always-on deployment is introduced.

## Validation

```bash
python -m unittest discover -s tests/autonomy -p 'test_*.py'
bash scripts/validate-pr.sh
```
