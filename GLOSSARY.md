# Glossary

## Agent

A specialist organizational role with an explicit contract, bounded responsibility, defined inputs and outputs, and no authority outside that contract.

## Artifact

A structured, versioned record produced by one stage and consumed by another. Artifacts are the formal communication layer between agents and the supervisor.

## Context package

The smallest sufficient set of task, project, architecture, standards, and profile information assembled for a specialist agent.

## Environment failure

A failure caused by missing or incompatible host tools, credentials, permissions, runtime capabilities, or local configuration. It is not a code defect.

## Infrastructure failure

A failure in an external service or transport dependency, such as GitHub, network access, CI service availability, or remote artifact storage.

## Lifecycle state

The single canonical GitHub label describing a work item's current organizational phase.

## Operational source of truth

The system whose current state governs workflow decisions. For Version 1 this is GitHub Issues, labels, pull requests, and Git history.

## Profile

Versioned project-specific configuration and knowledge used by generic agents. The initial profile is Godot plus School Saga.

## Repair

A bounded code-change attempt triggered only by an identified implementation, validation-code, or review defect.

## Retry

An explicit operator request to discard the prior attempt's recoverable implementation state and begin again from a clean base.

## Review

A subjective engineering assessment of correctness, maintainability, architecture, and coding standards. Review excludes CI, deployment, mergeability, and branch-protection evaluation.

## Supervisor

The sole orchestration component. It reconciles workflow state, prepares context packages, dispatches specialists, routes artifacts, and applies retry, recovery, and escalation policy without performing specialist work.

## Validation

Objective execution of deterministic checks outside the implementation agent. Validation reports observed results and classifies failures without judging design quality.

## Work item

A GitHub Issue representing a unit of requested engineering work.
