# Logging Model

## Goals

Logs must make the immediate failure easy to find without forcing an operator to read an entire agent transcript. They must support both human debugging and machine classification.

## Layered output

Every run has three layers.

### 1. Run summary

A compact ordered list of stages, duration, and outcome:

```text
Run: issue-80-attempt-3
✓ preflight        1.2s
✓ context          0.8s
✓ implementation  94.3s
✗ validation       6.7s  [environment]
```

The summary includes the primary failure, owner, and next action. It never embeds complete subprocess output.

### 2. Stage summary

Each stage emits a bounded summary containing:

- stage and role;
- command or operation;
- start/end time and duration;
- outcome and failure category;
- exit code when applicable;
- concise diagnosis;
- evidence and artifact references;
- next action.

### 3. Detailed logs

Full stdout, stderr, model transcript, and diagnostic data are stored separately and referenced by identifier. They should be collapsible in GitHub interfaces or downloadable as workflow artifacts.

## Stream handling

- stdout and stderr are captured separately.
- Encoding failures are handled explicitly and marked in metadata.
- Long output is retained in detailed storage, not truncated destructively.
- Human summaries may include a small bounded excerpt centered on the failure.
- Secrets and credentials are redacted before persistence.

## Structured stage event

Every stage emits a machine-readable event with at least:

```json
{
  "run_id": "issue-80-attempt-3",
  "stage": "validation",
  "role": "validator",
  "status": "failed",
  "category": "environment",
  "duration_ms": 6700,
  "exit_code": null,
  "summary": "Godot executable was not found.",
  "owner": "operator",
  "next_action": "Configure the required Godot executable and request retry.",
  "stdout_ref": "...",
  "stderr_ref": "...",
  "artifact_ref": "..."
}
```

## Agent transcript policy

Model transcripts are diagnostic evidence, not the primary log. They must not dominate the run summary. A transcript is stored separately and referenced only when needed to investigate agent behavior.

## Failure-first presentation

When a run fails, interfaces should present information in this order:

1. what failed;
2. failure category;
3. who owns the next action;
4. concise evidence;
5. exact next action;
6. links to detailed output and transcript.

## Correlation

Every log line, artifact, comment projection, commit, and workflow run must be correlatable through a run identifier and attempt number.

## Retention

Summaries and artifacts are retained for the life of the work order. Detailed logs may use configurable retention, but their deletion must not remove the structured outcome or failure evidence needed to explain a decision.
