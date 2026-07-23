# Artifact Model

Structured artifacts are the formal communication layer of the organization. They make every handoff inspectable, reproducible, and independent of hidden conversation history.

## Required properties

Every artifact must include:

- schema version;
- unique run identifier;
- repository and work-order identity;
- producing role and stage;
- start and completion timestamps;
- status;
- concise summary;
- evidence references;
- failure classification when applicable;
- recommended next action;
- immutable producer metadata.

## Core artifacts

### Context package

Produced by the Supervisor before implementation. Contains the issue, acceptance criteria, selected project documents, relevant ADRs and bible sections, constraints, and explicit exclusions.

### Implementation artifact

Produced by the Implementer. Records assumptions, changed files, implementation summary, known limitations, and any unresolved questions. It does not claim validation success.

### Validation artifact

Produced by the Validator. Records the exact command, host preflight result, exit code, duration, stdout/stderr references, objective checks, and failure category. It contains facts, not code-quality opinions.

### Review artifact

Produced by the Reviewer. Records findings about correctness, maintainability, architecture, and project standards. It must not include CI, deployment, mergeability, or branch-protection judgments.

### Repair artifact

Produced by the Repairer. Links the triggering validation or review finding to the changes made and the remaining repair budget.

### Merge artifact

Produced by the Merger. Records approval state, required CI status, branch protection, conflicts, merge method, and publication result.

### Run artifact

Produced and finalized by the Supervisor. Summarizes all stages and references their artifacts without embedding full logs.

## Storage in Version 1

GitHub and Git remain the source of truth. Artifact storage may use repository files, workflow artifacts, pull-request comments, or another GitHub-backed mechanism, provided that:

1. artifacts are durably addressable;
2. the latest artifact of each type is discoverable from the work order;
3. historical attempts are retained;
4. large logs are referenced rather than copied into summaries;
5. schema validation can be applied.

The exact storage adapter is deferred to platform implementation. Phase 2 defines semantics, not the final persistence mechanism.

## Immutability and supersession

Artifacts are append-only. A later attempt does not rewrite an earlier artifact. It creates a new artifact that identifies the superseded artifact and the reason for supersession.

## Evidence references

Artifacts should reference durable evidence such as:

- commit SHA;
- branch and pull-request number;
- GitHub Actions run/job identifier;
- log artifact identifier;
- repository file path and blob SHA;
- prior artifact identifier.

## Human-readable projection

Each artifact must support a short human-readable projection suitable for a GitHub comment:

```text
Stage: validation
Outcome: failed
Category: environment
Summary: Godot executable was not found on the configured host.
Owner: operator
Next action: install/configure the required Godot version, then set state:retry.
Details: <artifact reference>
```

The projection is not the artifact itself and must not replace structured data.
