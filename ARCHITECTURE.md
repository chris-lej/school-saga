# Organization Architecture

## Purpose

This document defines the Version 1 architecture of the School Saga autonomous software engineering organization.

GitHub is the operational source of truth. GitHub Issues represent work orders, labels represent workflow state, pull requests represent implementation deliverables, and Git records repository history. Structured artifacts are the formal communication mechanism between roles.

## Architectural boundaries

The organization is composed of one orchestrator and several bounded specialists:

- **Supervisor** owns workflow coordination, state transitions, context packaging, retry policy, artifact routing, and escalation.
- **Implementer** owns repository changes for one work order.
- **Validator** runs objective project checks outside the implementation agent.
- **Reviewer** evaluates code quality and project conformance, but does not judge CI, deployment, or mergeability.
- **Repairer** addresses code-caused validation or review findings within a bounded budget.
- **Merger** verifies publication gates and performs the merge.

No specialist owns another specialist's decision. The Supervisor coordinates decisions but does not replace them.

## Control plane and execution plane

### Control plane

The Supervisor and GitHub workflow state form the control plane. They decide what work is eligible, which role acts next, whether a retry is permitted, and when human intervention is required.

### Execution plane

Implementer, Validator, Reviewer, Repairer, and Merger form the execution plane. Each receives explicit inputs and produces a structured artifact plus any repository or GitHub side effects permitted by its contract.

## Communication model

Agents do not communicate through hidden chat history. Every handoff must be reproducible from:

1. GitHub issue and pull-request state;
2. repository contents and Git history;
3. project profile and selected context package;
4. structured artifacts;
5. stage logs.

## Project profiles

The platform architecture remains generic. Project-specific behavior is supplied through a profile that defines:

- technology and runtime requirements;
- validation commands;
- repository conventions;
- coding standards;
- architecture decisions;
- project constitution and bibles;
- context-selection rules.

School Saga will be the first Godot profile.

## Reliability principles

- Preflight detects missing tools, credentials, and invalid host configuration before implementation begins.
- Environment and infrastructure failures never enter code-repair loops.
- Code repair is bounded and evidence-driven.
- State transitions are explicit and mutually exclusive.
- Every stage is idempotent or has recovery evidence.
- Human overrides are explicit workflow actions, not hidden mutations.

## Phase 2 scope

Phase 2 defines the organization architecture, workflow state machine, artifact model, logging model, failure taxonomy, GitHub integration, recovery policy, and human-intervention boundaries. It does not implement production agents.