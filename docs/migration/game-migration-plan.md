# School Saga Game Migration Plan

Status: Active
Phase: 5 — Game Migration
Source repository: `chris-lej/school-saga-1`
Target repository: `chris-lej/school-saga`

## Objective

Migrate the playable Godot project from the legacy repository into the active repository while preserving behavior, provenance, and validation evidence.

The first migration goal is parity, not redesign. The migrated game should open and run in Godot with the same main scene, autoloads, input actions, scenes, scripts, resources, and tests as the legacy project.

## Confirmed source project

The legacy repository contains a Godot project named `School Saga` with:

- main scene: `res://scenes/locations/home_morning.tscn`;
- autoloads: `SceneTransition` and `SaveService`;
- player movement, interaction, cancel, and run input actions;
- Godot feature declaration for version 4.7 and Forward Plus rendering.

## Migration stages

### Stage 1 — Inventory

Create a complete manifest of the legacy project tree, grouped as:

- project configuration;
- scenes;
- scripts;
- resources and data;
- visual assets;
- audio and fonts;
- tests and validation tooling;
- CI and development tooling;
- legacy orchestration infrastructure.

Each entry must be classified as `migrate`, `adapt`, `archive`, or `exclude`.

### Stage 2 — Text project skeleton

Migrate text-based Godot and tooling files first, including:

- `project.godot`;
- `.gd`, `.tscn`, `.tres`, `.gdshader`, `.cfg`, `.json`, `.yaml`, `.md`, and test files;
- validation scripts and relevant CI configuration.

This stage must preserve resource paths exactly unless an explicit migration ADR changes them.

### Stage 3 — Binary assets

Migrate images, audio, fonts, and other binary assets using blob-safe Git operations. Verify file hashes or Git blob SHAs where practical.

### Stage 4 — Runtime parity

Validate that:

1. Godot imports the project without fatal errors;
2. the configured main scene loads;
3. autoload dependencies resolve;
4. player input and scene transitions function;
5. existing tests and validation commands pass or produce documented environment failures.

### Stage 5 — Separation from legacy automation

The game implementation may be migrated, but the superseded Worker-01 orchestration model must remain excluded from the active organization platform unless a component is explicitly audited and approved for reuse.

## Migration rules

- Do not silently redesign gameplay during transfer.
- Do not rename resource paths during parity migration without an ADR.
- Preserve source provenance in the migration manifest.
- Do not commit Godot import caches or local editor state.
- Keep unresolved source defects visible; do not mask them as migration success.
- Binary assets must not be reconstructed from descriptions.
- The target repository becomes canonical only after parity validation and merge.

## Completion criteria

Phase 5 is complete when the complete approved game tree has been transferred, the target repository can be opened as a Godot project, and validation evidence demonstrates parity or explicitly records every remaining blocker.
