# Implementation Roadmap

The platform will be implemented in phases. Each phase must produce an independently reviewable milestone and explicit acceptance criteria before the next phase begins.

## Phase 1 — Foundation

Define the product and its governing principles.

Deliverables:

- README
- Product Requirements Document
- Organization Manifesto
- Roadmap
- glossary and success criteria

Exit criteria:

- product scope is explicit;
- GitHub is accepted as the Version 1 operational source of truth;
- core principles and non-goals are documented;
- later phases can be evaluated against a stable baseline.

## Phase 2 — Organization Architecture

Define how work moves through the organization.

Deliverables:

- architecture overview;
- lifecycle state machine;
- state ownership and transition rules;
- artifact model;
- failure taxonomy;
- logging and observability specification;
- GitHub integration rules;
- recovery, retry, and human-intervention ADRs.

Exit criteria:

- every lifecycle state has one owner;
- every legal transition is documented;
- invalid and conflicting states are defined;
- environment, infrastructure, code, review, and policy failures have distinct handling paths.

## Phase 3 — Agent Contracts

Define the specialist roles before writing their implementations.

Initial contracts:

- Supervisor;
- Implementer;
- Validator;
- Reviewer;
- Repairer;
- Merger.

Each contract must include:

- mission;
- responsibilities;
- explicit non-responsibilities;
- inputs;
- outputs;
- produced and consumed artifacts;
- permitted state transitions;
- failure modes;
- success criteria.

Exit criteria:

- agent responsibilities do not overlap;
- Implementer has no CI or validation responsibility;
- Reviewer has no CI, deployment, or mergeability responsibility;
- Merger owns final merge prerequisites;
- Supervisor owns orchestration but performs no specialist work.

## Phase 4 — School Saga Profile

Create the first concrete project profile while keeping agent contracts generic.

Deliverables:

- profile manifest;
- supported Godot version and host requirements;
- project layout and naming conventions;
- GDScript, scene, resource, and asset conventions;
- validation commands and expected outputs;
- School Saga project constitution;
- architecture decision index;
- imported or referenced project bibles;
- context-selection rules.

Exit criteria:

- the profile provides sufficient context to implement and review a School Saga issue;
- project knowledge does not leak into generic agent contracts;
- bibles and architecture documents remain versioned sources of truth rather than copied prompt text.

## Phase 5 — Platform Implementation

Implement the organization incrementally.

Recommended order:

1. shared configuration and schemas;
2. GitHub workflow adapter;
3. supervisor and state reconciliation;
4. context packaging;
5. implementer runner;
6. validator runner;
7. reviewer runner;
8. merger runner;
9. repairer runner;
10. structured logging and run summaries.

Each component must be implemented and tested behind its contract before the next specialist is added.

Exit criteria:

- the documented happy path executes against a test issue;
- lifecycle exclusivity is enforced;
- every stage emits a structured artifact and concise summary;
- restart, retry, and blocked-state behavior are deterministic.

## Phase 6 — End-to-End Validation

Prove the system under normal and failure conditions.

Acceptance scenarios:

- successful issue-to-merge path;
- implementation defect repaired after failed validation;
- code-review changes requested and repaired;
- missing Godot or validation tool classified as environment failure;
- GitHub or network outage classified as infrastructure failure;
- explicit clean retry;
- process crash and checkpoint recovery;
- stale branch, stale pull request, or conflicting lifecycle labels;
- human block, abandonment, approval, and manual intervention;
- concise logs that identify the failing stage without requiring transcript archaeology.

Exit criteria:

- all acceptance scenarios are automated where feasible;
- remaining manual tests are documented and repeatable;
- failure paths do not violate agent contracts;
- School Saga can use the pipeline for real work.

## Phase 7 — Generalization

Extract reusable platform capabilities after the School Saga implementation is stable.

Deliverables:

- separation of generic platform code from the School Saga profile;
- documented profile interface;
- at least one contrasting example profile;
- migration guidance for additional repositories;
- evaluation of whether GitHub remains the workflow engine or becomes an adapter.

Exit criteria:

- adding another project does not require changing specialist contracts;
- project-specific validation and context are supplied through configuration;
- abstractions are derived from proven behavior rather than anticipated needs.

## Delivery policy

Each phase is delivered through its own branch and pull request. Production agent code is not introduced until Phases 1 through 4 have established accepted requirements, architecture, contracts, and School Saga profile boundaries.
