# World Scene Contract

School Saga uses a reusable map contract for walkable 2D locations. The purpose is to let home, neighborhood, school, and validation maps share collision and authoring rules without committing to complete production maps yet.

## Memory intent

Walkable locations should support curiosity through believable boundaries: walls, furniture, gates, sidewalks, and doorways make the place feel authored, while intended paths remain open for exploration.

## Required root structure

Walkable location scenes use a `Node2D` root with `res://src/world/walkable_world_scene.gd` attached. Development builds validate the contract on `_ready()`.

Required direct children:

- `VisualLayers`: non-physics map art, ordered back to front by child order or `z_index`.
- `Collision`: solid `StaticBody2D` boundaries and obstacles.
- `Interactables`: `Area2D` sensors for inspectable objects and future interaction checks.
- `SpawnPoints`: `Marker2D` nodes. Every playable map must include `PlayerStart`.
- `Exits`: `Area2D` sensors for scene exits. These detect the player but do not block movement.
- `ForegroundOcclusion`: visual foreground pieces and optional occlusion sensors.
- `NavigationMarkers`: `Marker2D` waypoints for future NPC routing and authored routines.
- `Player`: an instance of `res://scenes/actors/player.tscn` when the map is directly playable.

## Collision layers

Layer names are centralized in `project.godot` and mirrored as bit constants in `res://src/world/world_collision_layers.gd`.

| Layer | Name | Constant | Use |
| --- | --- | --- | --- |
| 1 | `player` | `WorldCollisionLayers.PLAYER` | Player `CharacterBody2D`. |
| 2 | `world_solid` | `WorldCollisionLayers.WORLD_SOLID` | Walls, furniture, fences, map boundaries, closed doors. |
| 3 | `interactable_sensor` | `WorldCollisionLayers.INTERACTABLE` | Non-blocking inspection or conversation areas. |
| 4 | `exit_sensor` | `WorldCollisionLayers.EXIT` | Non-blocking scene-transition areas. |
| 5 | `foreground_occlusion` | `WorldCollisionLayers.FOREGROUND_OCCLUSION` | Optional non-blocking foreground fade or cover sensors. |

Masks:

- Player layer: `player`; mask: `world_solid`.
- Solid bodies layer: `world_solid`; mask: `player`.
- Interactable, exit, and occlusion areas use their sensor layer and mask `player`.

## Authoring rules

- Use `StaticBody2D` with enabled `CollisionShape2D` children for walls, furniture, fences, and map boundaries.
- Keep intended doorways and paths physically open. Put `Area2D` exit sensors in the opening instead of using solids as doors unless the door is meant to be closed.
- Keep interactables non-blocking by authoring them as `Area2D` sensors, not `StaticBody2D`, unless the object should also obstruct movement.
- Spawn points are markers, not scripts. `PlayerStart` is the default entry marker for directly playable maps.
- Foreground occlusion should remain non-blocking unless the same object also has a separate solid under `Collision`.
- Navigation markers are authored hints. They do not define walkability by themselves.
- TileMap collisions may be used later if they follow the same layer and mask assignments. The representative scene uses explicit `StaticBody2D` nodes because that is the smallest maintainable approach in the current repository.

## Validation

`res://scenes/validation/collision_playground.tscn` is the current map-authoring playground. It demonstrates:

- left, right, bottom, and partial top map boundaries;
- a wall segment obstacle;
- a furniture obstacle;
- an open north doorway with a non-blocking exit sensor;
- `PlayerStart`, foreground occlusion, and navigation marker groups;
- a bounded follow camera.

Headless coverage lives in `res://tests/godot/world_scene_contract_test.gd`. The shared gate in `scripts/validate-pr.sh` runs the contract test and loads the playground before Web export. The test validates the node contract and confirms that solid obstacles block movement while the doorway and exit sensor remain traversable.
