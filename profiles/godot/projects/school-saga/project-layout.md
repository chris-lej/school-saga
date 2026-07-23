# School Saga Project Layout

This document defines the intended repository zones. It is a profile contract, not evidence that every directory already exists.

```text
./
  project.godot
  scenes/                 Reusable and composed Godot scenes
  scripts/                Runtime GDScript organized by subsystem
  resources/              Authored Godot resources and data definitions
  assets/                 Source art, audio, fonts, and other authored assets
  tests/                  Automated behavioral and integration tests
  tools/                  Editor tooling and developer utilities
  scripts/                Repository automation and validation entry points
  docs/                   Product and engineering documentation
  profiles/               Platform technology and project profiles
  artifacts/              Generated run artifacts; not authored product truth
```

## Ownership rules

- Runtime systems belong under `scripts/` and should follow subsystem boundaries documented in `architecture/`.
- Scene files belong under `scenes/`; reusable scenes should not depend on unrelated top-level scenes.
- Authored game data belongs under `resources/` rather than being embedded in automation.
- Source assets belong under `assets/`; imported caches and generated derivatives are not hand-edited.
- Tests belong under `tests/` and must be runnable by the declared validation entry point.
- Developer and editor tooling belongs under `tools/` and must not become a hidden runtime dependency.
- Repository automation belongs under `scripts/` and must return reliable exit codes.
- Generated autonomous-run output belongs under `artifacts/` or external GitHub artifacts and is not committed unless the profile explicitly requires fixtures.

## Change boundaries

Agents must preserve the existing repository structure when it conflicts with this target layout unless an issue explicitly authorizes migration. Structural changes require an ADR when they alter subsystem ownership, compatibility surfaces, or validation entry points.
