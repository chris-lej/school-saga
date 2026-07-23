# GitHub Integration

## Version 1 decision

GitHub is the workflow engine and operational source of truth for Version 1.

- Issues represent work orders.
- Canonical labels represent workflow state.
- Pull requests represent implementation deliverables.
- Git commits and branches represent repository history.
- GitHub Actions may execute objective validation and publication gates.
- Comments provide human-readable projections of structured artifacts.

## Supervisor responsibilities

The Supervisor is the only automated component authorized to mutate canonical state labels. It may also:

- inspect issue priority and dependencies;
- create or reconcile implementation branches;
- dispatch role-specific work;
- attach artifact projections to issues or pull requests;
- preserve run and attempt identity;
- apply bounded retry and escalation policies.

## Specialist restrictions

- Implementer does not change issue labels, create pull requests, inspect CI, or merge.
- Validator does not change issue labels or request code changes directly.
- Reviewer does not inspect or gate on CI, deployment, branch protection, or mergeability.
- Repairer changes code only in response to an authorized finding artifact.
- Merger may inspect CI, approvals, branch protection, and conflicts, but does not reinterpret code quality.

## Polling and idempotency

Version 1 may use polling. Every poll cycle must be safe to repeat:

1. inspect durable GitHub state;
2. reconcile with local checkpoint and artifact evidence;
3. perform at most one externally visible transition or bounded stage;
4. persist evidence before the next cycle.

A process restart must not cause duplicate implementation, duplicate pull requests, or repeated merges.

## Labels

Canonical workflow labels are defined by the state-machine document. Diagnostic details belong in artifacts and comments, not additional lifecycle labels. Auxiliary labels may identify priority, project profile, or assigned role.

## Comments

Comments are concise projections, not complete logs. Each automated comment should contain:

- run and attempt identifier;
- stage outcome;
- concise summary;
- owner and next action;
- reference to the structured artifact or detailed logs.

## Pull requests

The Supervisor creates or reconciles the pull request after implementation and successful objective validation. The pull request description must reference the work order, implementation artifact, and validation artifact.

Review findings are attached to the pull request through a review artifact projection. CI and merge gates are evaluated later by the Merger.

## Human overrides

Humans may explicitly:

- prioritize or reprioritize work;
- set `state:retry`;
- block or abandon work;
- approve or reject a pull request;
- merge when repository permissions allow.

An override is recorded as a GitHub event and must be reconciled by the Supervisor rather than silently overwritten.

## Future adapter boundary

Although GitHub is authoritative in Version 1, the architecture should isolate GitHub-specific operations behind an adapter so the organization model, agent contracts, artifacts, failure taxonomy, and project profiles can later support another workflow backend.