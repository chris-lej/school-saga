# Autonomy v2 constrained code-editing Worker

This slice introduces an explicitly enabled Worker capable of applying a bounded file-change plan to an allowlisted local repository workspace. It remains fail-closed and cannot review or merge pull requests.

## Operating boundary

The Worker is disabled unless `enabled=True` is supplied by trusted runtime configuration.

Execution additionally requires:

- an allowlisted repository;
- an allowlisted file path for every change;
- a bounded number of changed files;
- a bounded total patch size;
- a bounded Worker attempt count;
- a persisted job in a Worker-owned lifecycle state;
- a plan whose issue number matches the persisted job;
- draft-pull-request-only policy;
- passing repository validation before pull-request creation.

Issue text is not executed. Commands continue to come exclusively from trusted repository validation configuration.

## Path safety

`LocalWorkspaceBackend` rejects:

- absolute paths;
- `..` traversal;
- paths outside configured prefixes;
- parent-directory symlink escapes;
- overwriting an existing symlink;
- plans exceeding file-count or patch-size limits.

The backend records a deterministic workspace ID, changed-file list, patch digest, base SHA, and synthetic commit SHA for fixture and integration testing. A later real Git backend must preserve these contracts and add actual index/commit operations.

## Lifecycle

The guarded Worker accepts `claimed` or `executing` jobs and advances them to `validating`.

It persists:

- workspace metadata;
- branch mutation result;
- validation result linkage;
- draft pull-request mutation result;
- typed `WorkerResult` with commit SHA and PR number when available;
- structured audit events.

Stable operation IDs prevent duplicate workspace preparation, branch creation, validation, and pull-request creation after restart.

## GitHub mutation guards

Branch intent includes `expected_base_sha`.

Draft pull-request intent includes:

- `draft: true`;
- `expected_head_sha`;
- explicit base branch;
- stable operation ID.

The production transport must preserve these guards. Reviewer and Merger remain independently configured and cannot be enabled by this Worker.

## Current limitations

This initial slice does not:

- invoke a coding model;
- translate arbitrary issue prose into file changes;
- create a real Git commit locally;
- install a live GitHub client;
- submit reviews;
- merge pull requests;
- run continuously.

A trusted caller supplies a typed `CodeEditPlan`. Production use requires a separately reviewed planning/model backend and a real Git workspace implementation.

## Validation

```bash
python -m unittest discover -s tests/autonomy -p 'test_*.py'
bash scripts/validate-pr.sh
```
