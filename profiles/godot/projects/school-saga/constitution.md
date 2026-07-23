# School Saga Constitution

This constitution defines the non-negotiable engineering principles for School Saga.

## Product integrity

1. Preserve the intended player experience and established project direction.
2. Do not invent narrative, character, visual, or gameplay canon when the supplied context is incomplete.
3. Keep changes aligned with the issue's acceptance criteria and explicitly supplied design material.
4. Prefer incremental evolution over speculative subsystem replacement.

## Engineering integrity

5. Favor readability, maintainability, and explicit ownership over cleverness.
6. Avoid unnecessary dependencies, abstractions, and framework layers.
7. Preserve save data, scene contracts, resource paths, signals, and public APIs unless a breaking change is explicitly approved.
8. Separate runtime code, editor tooling, generated content, and automation.
9. Treat validation, review, and merge as independent organizational responsibilities.
10. Classify failures before deciding whether code repair is appropriate.

## Autonomous-operation boundaries

11. The Implementer changes repository content and then stops.
12. The Validator determines whether the software works and reports objective evidence.
13. The Reviewer evaluates correctness, architecture, maintainability, and project conformance without owning CI or mergeability.
14. The Merger owns branch protection, CI state, approval gates, and publication.
15. Only the Supervisor changes canonical workflow state.
16. Agents communicate through declared artifacts and GitHub state, never through hidden direct handoffs.

## Human authority

17. Humans define product intent, approve exceptions, and resolve ambiguous or conflicting project policy.
18. Missing authority is a reason to block, not permission to guess.
19. Every autonomous action must be reproducible from repository state, profile version, context package, and recorded artifacts.
