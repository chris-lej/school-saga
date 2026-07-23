# Organization Manifesto

## Mission

Build School Saga through an autonomous software engineering organization whose behavior is predictable, explainable, and recoverable.

Humans define intent. Agents execute intent. The platform preserves control and evidence.

## Principles

### One responsibility per agent

Each agent owns one bounded organizational responsibility. Agent responsibilities do not overlap.

### Explicit contracts

Every agent contract defines its mission, responsibilities, non-responsibilities, inputs, outputs, artifacts, state transitions, failure modes, and success criteria.

Agents are roles, not personalities.

### GitHub is the Version 1 source of truth

GitHub Issues define work. Labels define lifecycle state. Pull requests define proposed deliverables. Git defines implementation history.

### Artifacts are the communication layer

Agents exchange structured artifacts rather than relying on hidden conversation history. Artifacts must be inspectable by humans and machines.

### Validation is objective

Validation reports what happened when deterministic checks ran. It does not judge design quality.

### Review is independent

Review evaluates the submitted code for correctness, maintainability, architecture, and project standards. Review does not block on CI, deployment, permissions, merge conflicts, or branch protection.

### Environment is not implementation

Missing tools, credentials, network access, service availability, or host capabilities are environment or infrastructure failures. They must never be presented to an implementation agent as code defects.

### Humans own intent

Agents do not invent product goals. Humans may prioritize, retry, block, abandon, approve, cancel, and intervene.

### Project knowledge is pluggable

General organizational behavior is separated from School Saga and Godot knowledge. Project-specific context is provided through a versioned profile.

### Context is selected, not dumped

Agents receive the smallest sufficient context package for their assignment. A task should not require every project document to be loaded indiscriminately.

### Everything is reproducible

Every decision must be explainable from GitHub state, versioned configuration, produced artifacts, and stage logs.

### Failures are classified before action

Automated repair is allowed only for code-related failures. Environment, infrastructure, and policy failures escalate through their designated paths.

### Boring is a feature

The orchestration layer should be simple, deterministic, and observable. Domain intelligence belongs in project profiles and specialist context, not hidden inside workflow control.
