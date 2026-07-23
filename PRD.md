# Product Requirements Document

## Product

School Saga Autonomous Engineering Organization is a GitHub-centered autonomous software delivery system for the School Saga Godot project.

It is the first concrete implementation of a broader, project-agnostic organizational model. Version 1 intentionally uses GitHub Issues, labels, pull requests, and Git as the operational source of truth.

## Problem

The existing worker pipeline has demonstrated that autonomous implementation is feasible, but it has also exposed recurring systemic problems:

- overlapping agent responsibilities;
- implementation agents being held responsible for CI or host-environment failures;
- reviewers blocking changes for pipeline concerns outside code review;
- unclear ownership of retries, recovery, mergeability, and validation;
- transient failures being represented inconsistently;
- logs containing too much run history and too little failure-focused information;
- project context being passed inconsistently and sometimes excessively;
- worker behavior being difficult to reason about after interruptions.

## Goal

Create a predictable autonomous engineering organization in which each specialized agent owns exactly one responsibility, communicates through structured artifacts, and advances work through explicit GitHub workflow states.

The primary success criterion is not merely merged pull requests. It is reproducible, explainable, and recoverable autonomous behavior.

## Users

### Human operator

Defines intent, creates and prioritizes work, resolves environment problems, requests retries, approves exceptions, and may manually merge or cancel work.

### Supervisor

Coordinates the workflow, assembles context packages, dispatches specialist agents, routes artifacts, and applies recovery and escalation policy.

### Specialist agents

Implementer, Reviewer, Validator, Repairer, and Merger. Each operates under a narrow contract.

## Product principles

1. One responsibility per agent.
2. GitHub is the operational source of truth for Version 1.
3. Structured artifacts are the communication layer.
4. Validation is objective and external to the implementation agent.
5. Review evaluates code, not CI, deployment, or mergeability.
6. Environment and infrastructure failures are not implementation failures.
7. Humans define intent; agents execute intent.
8. Every decision must be reconstructable from GitHub state, artifacts, and logs.
9. Project knowledge is supplied through a project profile.
10. Retry is explicit, bounded, and observable.

## Initial workflow states

The canonical lifecycle states are:

- `state:ready`
- `state:implementing`
- `state:review`
- `state:merge`
- `state:done`

Exception states are:

- `state:blocked`
- `state:retry`
- `state:abandoned`

Exactly one lifecycle state may be present on a work item at a time.

## Initial roles

### Supervisor

Owns orchestration only.

### Implementer

Owns repository implementation changes only. It does not run CI, merge, manipulate GitHub workflow state, or determine whether host validation infrastructure is healthy.

### Validator

Runs objective validation outside the implementation agent and emits structured results.

### Reviewer

Evaluates correctness, maintainability, architecture, and coding standards. It does not evaluate CI status, deployment state, mergeability, branch protection, or repository permissions.

### Repairer

Repairs code only when validation or review identifies a code defect. It does not repair environment or infrastructure failures.

### Merger

Evaluates merge prerequisites, including required approvals, CI status, branch protection, conflicts, and publication policy, then merges when permitted.

## Project profile

School Saga will be represented as a Godot-specific project profile containing:

- supported Godot version;
- project layout and naming conventions;
- GDScript standards;
- scene and resource conventions;
- validation commands and expected host tools;
- project constitution;
- architecture decisions;
- design, world, story, and gameplay bibles;
- context-selection rules.

Agents remain generic and receive only the profile-derived context needed for the current task.

## Logging requirements

Every run and stage must produce:

- a concise stage summary;
- status and duration;
- failure category when unsuccessful;
- a short actionable failure explanation;
- separate stdout and stderr capture where applicable;
- links or references to detailed logs;
- a machine-readable result artifact.

The default human-facing view must prioritize the failing stage rather than replaying the full agent transcript.

## Failure taxonomy

Every unsuccessful stage must be classified as exactly one of:

- implementation;
- review;
- validation-code;
- environment;
- infrastructure;
- policy;
- human-intervention-required.

Only code-related failures may enter an automated repair loop.

## Human controls

Humans may:

- create and prioritize work;
- move work to `state:retry`;
- block, abandon, approve, or cancel work;
- resolve environment and infrastructure problems;
- override automated progression where repository policy permits.

Automated components must never silently bypass required validation or fabricate successful artifacts.

## Non-goals for the first implementation

- supporting multiple project profiles;
- replacing GitHub as the workflow engine;
- a general-purpose agent framework;
- autonomous product strategy or invention of business goals;
- agents communicating through hidden conversational memory;
- production implementation before contracts and schemas are accepted.

## Success metrics

The first School Saga implementation is successful when:

- every lifecycle state has one clear owner;
- agents do not make decisions outside their contracts;
- environment failures never trigger code-repair attempts;
- reviewer decisions are independent of CI and merge status;
- every failed run surfaces a concise actionable summary;
- interrupted runs can be resumed or explicitly retried without manual repository surgery;
- the full decision path is reconstructable from GitHub state and artifacts;
- an end-to-end issue can move from ready to done under the documented contracts.
