# Autonomy v2 foundation

This package is tooling for the repository and is isolated from the Godot game runtime. It currently performs no GitHub mutations, code generation, reviews, or merges.

## Contracts

The code in `autonomy/contracts.py` defines schema-versioned representations for repository targets, issue work requests, worker results, validation results, review results, merge decisions, jobs, and audit events.

The initial lifecycle is:

```text
queued -> claimed -> executing -> validating -> reviewing -> approved -> merging -> completed
```

`blocked`, `failed`, and `cancelled` are terminal exception states. Validation and review may return a job to `executing` for another attempt. Every transition is explicit; invalid transitions fail with the current state and allowed targets.

## Local store

`JsonJobStore` persists jobs, audit events, and operation IDs to one JSON file. Writes use a temporary file followed by an atomic replacement. Reusing an operation ID returns the previously persisted result rather than duplicating the transition or audit event.

This backend is intentionally small and local. Agents should depend on the store interface rather than the JSON format so a transactional backend can replace it later.

## Fixture CLI

The CLI requires only Python 3.11 or newer and does not require GitHub credentials.

```bash
python -m autonomy.cli --store /tmp/school-saga-jobs.json create \
  --repo chris-lej/school-saga \
  --issue 39 \
  --title "Autonomy v2 foundation" \
  --operation-id create-39
```

Copy the returned `job_id`, then inspect and transition it:

```bash
python -m autonomy.cli --store /tmp/school-saga-jobs.json inspect JOB_ID
python -m autonomy.cli --store /tmp/school-saga-jobs.json transition JOB_ID claimed --operation-id claim-39
python -m autonomy.cli --store /tmp/school-saga-jobs.json events --job-id JOB_ID
```

Repeating the transition command with the same operation ID is safe and does not create another event.

## Tests

Run the foundation tests with the standard library test runner:

```bash
python -m unittest discover -s tests/autonomy -p 'test_*.py'
```

The existing Godot repository gate remains authoritative for game changes:

```bash
bash scripts/validate-pr.sh
```

## Safety boundary

This foundation does not start Worker, Reviewer, or Merger processes. It does not access credentials or alter GitHub. Those capabilities will be introduced as separate reviewed slices after the job substrate is stable.
