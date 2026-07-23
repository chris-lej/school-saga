# School Saga Coding Standards

These standards supplement the generic Godot profile.

## Scope discipline

- Implement only the issue's accepted behavior.
- Avoid opportunistic refactors unless required for correctness.
- Keep commits and diffs organized around one responsibility.
- Preserve existing behavior outside the requested change.

## Design and architecture

- Place behavior in the subsystem that owns it.
- Prefer composition over deep inheritance.
- Keep domain rules separate from presentation and editor tooling.
- Introduce global services only through an approved ADR.
- Document new public interfaces and cross-subsystem dependencies.

## GDScript and Godot

- Use typed signatures for public and cross-subsystem interfaces.
- Treat signals, exported properties, resource formats, node paths, and save fields as compatibility contracts.
- Avoid silent fallback behavior that hides invalid configuration.
- Emit actionable errors at configuration boundaries.
- Keep deterministic game logic independent of frame timing where practical.

## Testing and documentation

- Add tests for new behavior and regressions when a test seam exists.
- Update architecture or Bible material only when the issue authorizes a product or system decision.
- Do not invent missing canon to complete an implementation.
- Explain unavoidable migrations and breaking changes in the implementation artifact.

## Generated content

- Do not commit transient logs, local caches, imported artifacts, or autonomous-agent transcripts.
- Commit generated files only when they are intentional source fixtures and their generation method is documented.
