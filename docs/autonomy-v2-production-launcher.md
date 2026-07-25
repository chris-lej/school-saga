# Autonomy v2 concrete production launcher

This launcher is the final operator boundary before bounded autonomous coding. It loads trusted deployment configuration, requires concrete readiness and lifecycle adapters, validates the declared environment-variable references, and dispatches the live CLI commands.

## Required environment

The trusted deployment JSON names environment variables for:

- the GitHub token;
- the readiness signing key;
- the emergency stop.

The launcher checks that all three variables exist before composing the runtime. It never prints their values.

## Launch progression

1. Update the repository checkout and record the exact current `main` SHA.
2. Confirm the worktree is clean.
3. Configure non-empty path, validation-command, mutation, and required-check allowlists.
4. Set the GitHub token, readiness signing key, and emergency-stop variables.
5. Generate and verify a current signed READY report.
6. Run the readiness command. It must perform no mutation.
7. Run observe-only mode and inspect the lease and persisted deployment state.
8. Run exactly one low-risk `state:ready` canary issue in single-cycle mode.
9. Inspect the branch, commit SHA, validation, pull request, review decisions, expected-head checks, merge result, and operation IDs.
10. Promote to bounded always-on mode only after multiple clean canaries.

## Failure boundaries

Startup fails closed when:

- deployment configuration is disabled or incomplete;
- a required secret or emergency-stop environment variable is missing;
- readiness verification fails or has expired;
- `main` moved from the signed readiness binding;
- the scheduler lease is owned by another live process;
- the emergency stop is active;
- required checks, audit persistence, or repository state cannot be verified.

## Canary acceptance

A canary is acceptable only when:

- exactly one explicitly selected issue runs;
- the Worker changes only allowlisted paths;
- validation passes;
- the Reviewer evaluates the exact current head SHA;
- requested fixes remain bounded and revalidated;
- the Merger verifies approval, checks, and exact head before merging;
- every mutation and lifecycle transition is present in the audit trail;
- restart does not duplicate claims, branches, commits, pull requests, reviews, or merges.

## Rollback

1. Activate the emergency stop.
2. Pause, drain, or shut down the scheduler.
3. Revoke or rotate the GitHub token when remote state is uncertain.
4. Preserve readiness, lease, deployment, job, operation, review, merge, and audit records.
5. Quarantine uncertain issues and branches.
6. Require a new signed READY report.
7. Restart in readiness and observe-only modes before any further work.

## Validation

```bash
python -m unittest discover -s tests/autonomy -p 'test_*.py'
bash scripts/validate-pr.sh
```
