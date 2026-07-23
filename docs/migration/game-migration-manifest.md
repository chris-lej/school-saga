# School Saga Game Migration Manifest

Status: In progress
Source repository: `chris-lej/school-saga-1`
Source branch: `main`
Target branch: `phase-5/game-migration-foundation`

## Classification

- `migrate`: required for game parity;
- `adapt`: required, but target integration must change;
- `archive`: preserve as historical engineering evidence only;
- `exclude`: generated, local, secret, or superseded material.

## Confirmed root configuration

| Source path | Classification | Evidence | Notes |
|---|---|---|---|
| `project.godot` | migrate | blob `2a527b1173c966e02069f03178ee518a4d001f36` | Godot 4.7 project; main scene `scenes/locations/home_morning.tscn`; autoloads `SceneTransition` and `SaveService`. |

## Confirmed dependencies from `project.godot`

| Referenced path | Classification | Status |
|---|---|---|
| `scenes/locations/home_morning.tscn` | migrate | inventory pending |
| `src/core/scene_transition.gd` | migrate | inventory pending |
| `src/core/save_service.gd` | migrate | inventory pending |

## Inventory groups

The following groups must be enumerated before bulk transfer:

- [ ] `.github/` workflows relevant to game validation;
- [ ] `assets/` and all binary media;
- [ ] `scenes/`;
- [ ] `src/` or other script directories;
- [ ] game data and resources;
- [ ] tests;
- [ ] validation commands and scripts;
- [ ] Godot import metadata intentionally tracked by the source;
- [ ] external addons and licenses.

## Explicit exclusions

These categories are excluded unless later approved by an implementation audit:

- `.godot/` import caches and editor-local state;
- secrets, tokens, credentials, and machine-specific paths;
- Worker-01 queue orchestration and checkpoint implementation;
- generated build output;
- local logs and temporary artifacts.

## Provenance policy

Every migrated batch must identify:

1. the source repository;
2. the source commit or blob SHA;
3. the transferred paths;
4. whether content was copied exactly or adapted;
5. validation performed after transfer.

## Current limitation

The GitHub connector exposes repository files by known path but does not provide a recursive tree listing in the currently available actions. The next inventory pass will discover the game tree from confirmed configuration references, commit history, pull-request file lists, and targeted path searches. Binary transfer will use Git blobs and trees rather than UTF-8 file actions.
