# ADR-001: Agent Boundaries

- Status: Accepted for Version 1
- Date: 2026-07-23

## Context

Earlier School Saga automation allowed implementation, validation, review, and publication concerns to overlap. This produced ambiguous ownership, false repair loops, and agents blocking work for conditions outside their responsibility.

## Decision

The organization uses bounded roles with one primary responsibility each:

- Supervisor coordinates workflow and is the only automated canonical-state mutator.
- Implementer changes repository content only.
- Validator produces objective execution evidence outside the implementation agent.
- Reviewer evaluates correctness, maintainability, architecture, and project standards only.
- Repairer addresses authorized code findings within a bounded budget.
- Merger evaluates publication gates and merges.

Every role contract must state explicit non-responsibilities.

## Consequences

- CI is not an Implementer or Reviewer concern.
- Missing host tools cannot be assigned to code repair.
- Handoffs require structured artifacts.
- The Supervisor coordinates but cannot fabricate specialist decisions.
- Some workflows require more stages, but each stage becomes easier to test and debug.
