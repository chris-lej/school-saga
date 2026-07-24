# Migration Parity Manifest

## Purpose

This document records the Phase 5 migration status from `chris-lej/school-saga-1` into `chris-lej/school-saga`.

The migration goal is runtime and product parity for the playable first-school-day slice, not a byte-for-byte copy of the legacy repository. Legacy autonomous-agent orchestration is intentionally excluded unless a specific active-repository need is identified.

## Migrated runtime and content

The active repository now contains the first-pass playable route:

`home morning → Rua do Monte neighborhood threshold → Colégio Monte Araucária first day → return home`

Migrated or reconstructed gameplay coverage includes:

- opening character entry, bedroom, breakfast choice, and neighborhood threshold;
- Brazilian neighborhood atmosphere and procedural ambient audio;
- fixed-resolution neighborhood visual-style validation;
- school courtyard routines, classroom seating, relationship consequences, independent NPC behavior, recess basketball, and the unresolved rumor loop;
- return-home evening consequences and completed-day persistence;
- reusable player movement, directional presentation, bounded follow camera, world collision layers, scene validation, and collision playground;
- save/load services and scene-transition services;
- Godot Web export, Vercel static deployment contract, and export validation;
- focused Godot tests plus one end-to-end vertical-slice route test.

## Migrated documentation

The active repository includes adapted documentation for:

- vertical-slice intent and acceptance criteria;
- player foundation;
- walkable-world scene contracts;
- visual-style validation;
- validation policy;
- Web deployment.

Documentation was adapted where the active repository differs from the legacy Worker-01 execution model.

## Superseded or intentionally excluded

The following legacy areas are not part of the game migration:

- Worker-01 implementation polling and recovery;
- Reviewer-01 review and repair orchestration;
- Merge-01 autonomous merge control;
- agent supervisor processes, event buses, Discord alerting, and related Windows operations;
- legacy agent contracts, label-driven dispatch, and automation-specific tests;
- historical CI wiring whose purpose was enforcing those autonomous-agent workflows.

These systems are excluded because the active repository migration is being performed through focused human-reviewed pull requests and the shared repository validation gate.

## Remaining integration work

The core legacy gameplay slice is present, but these items remain product-development work rather than missing legacy parity:

- convert the neighborhood threshold into a fully walkable authored map using the migrated player/world contracts;
- integrate final production art and animation assets in place of procedural or placeholder presentation;
- expand save/resume entry points so a player can resume directly into every major phase with complete state restoration;
- add broader usability, browser, controller, performance, and accessibility testing;
- perform a final manual playthrough and visual/audio review of the exported Web build.

## Phase 5 completion criteria

Phase 5 can be considered complete when:

- the shared `scripts/validate-pr.sh` gate passes on `main`;
- the end-to-end vertical-slice test covers the continuous migrated route;
- all retained legacy gameplay, runtime, deployment, and validation contracts are represented in the active repository;
- excluded legacy automation remains explicitly documented rather than silently omitted;
- remaining tasks are clearly product improvements, not undiscovered migration gaps.
