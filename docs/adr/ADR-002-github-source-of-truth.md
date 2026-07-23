# ADR-002: GitHub as the Version 1 Source of Truth

- Status: Accepted for Version 1
- Date: 2026-07-23

## Context

The first implementation must be concrete and operable without introducing a separate database or workflow service. The existing operating model already uses GitHub issues, labels, pull requests, Git history, and Actions.

## Decision

GitHub is the operational source of truth for Version 1:

- issues are work orders;
- canonical labels are workflow state;
- pull requests are implementation deliverables;
- Git is repository history;
- GitHub-backed artifacts and comments expose stage evidence.

GitHub-specific behavior should be isolated behind an adapter boundary so the organization model can later support another backend.

## Consequences

- Polling is acceptable in Version 1 when operations are idempotent.
- External GitHub mutations must be reconciled rather than overwritten blindly.
- Artifact semantics remain platform-defined even when persistence is GitHub-backed.
- Generalization to another workflow engine is deferred until the School Saga reference pipeline is stable.
