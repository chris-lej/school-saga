# Player Foundation

School Saga uses a reusable 2D player foundation at `res://scenes/actors/player.tscn`.

## Scene Contract

The scene root is a `CharacterBody2D` named `Player` with `res://src/player/player_controller_2d.gd` attached.

Required child nodes:

- `CollisionShape2D`: enabled physical body shape for map collisions.
- `PlayerAnimatedSprite`: visible `AnimatedSprite2D` presentation node with the required directional animation states.
- `InteractionAnchor`: `Marker2D` positioned in the current facing direction for later interaction checks.
- `FacingDirectionMarker`: `Marker2D` mirroring the facing direction for debug visibility and future animation wiring.

The scene is map-agnostic. Location scenes instantiate it and provide their own camera, map collision, spawn placement, and transitions. Walkable maps follow `docs/world-scene-contract.md`; by default the player uses the `player` physics layer and collides with the `world_solid` layer only.

## Camera Contract

Maps that need player-follow behavior add a `Camera2D` with `res://src/camera/follow_camera_2d.gd` attached. The reusable player scene does not own this camera.

Required map-side camera configuration:

- `target_path`: `NodePath` pointing to the map's player instance.
- `world_bounds`: `Rect2` in world coordinates covering the area the camera may show.

Configurable behavior includes smoothing, zoom, dead-zone size, and an optional deterministic viewport override for tests. When the world bounds are smaller than the visible viewport on an axis, the camera centers that axis instead of attempting an impossible clamp. HUD and other screen-space UI belong under `CanvasLayer` or normal `Control` roots outside the world camera hierarchy.

## Movement Contract

Movement runs from `_physics_process()` and uses `move_and_slide()`.

Runtime properties intended for later systems:

- `movement_speed`: exported movement speed in pixels per second.
- `facing_direction`: last non-zero normalized movement direction.
- `facing_animation_direction`: last cardinal presentation direction: `down`, `up`, `left`, or `right`.
- `is_moving`: whether movement input is active.
- `movement_direction`: normalized current movement input.

`PlayerController2D` drives `PlayerAnimatedSprite` from movement state and facing direction. When movement stops, the controller preserves the last cardinal direction and switches from `walk_*` to the matching `idle_*` pose. Diagonal movement is normalized so it is not faster than cardinal movement.

## Presentation and Asset Contract

The player scene uses `AnimatedSprite2D` with Godot `SpriteFrames`, allowing final art to replace placeholder frames without rewriting controller logic.

Required animation names:

- `idle_down`
- `idle_up`
- `idle_left`
- `idle_right`
- `walk_down`
- `walk_up`
- `walk_left`
- `walk_right`

The current repository-safe placeholder sheet is `res://assets/player/player_placeholder_directional.png`. Its exact image format, atlas regions, and frame dimensions are implementation details covered by the non-blocking advisory validation. Replacement art must preserve the animation names and update `res://scenes/actors/player.tscn` rather than changing controller behavior. Pixel-art presentation uses nearest texture filtering so frames remain crisp when scaled.

## Input Contract

The project input map defines these stable actions:

- `player_move_left`: keyboard left movement and controller equivalents.
- `player_move_right`: keyboard right movement and controller equivalents.
- `player_move_up`: keyboard upward movement and controller equivalents.
- `player_move_down`: keyboard downward movement and controller equivalents.
- `player_interact`: keyboard and controller interaction input.
- `player_cancel`: keyboard and controller cancellation input.
- `player_run`: keyboard and controller run input.

`PlayerController2D` exposes action-name exports for movement, interaction, cancel, and run so future maps, test scenes, or a remapping interface can override action names without hard-coded key checks. A complete remapping UI and mobile virtual joystick are outside the current foundation.

## Validation

`res://scenes/validation/player_movement_validation.tscn` instantiates the player in a plain `Node2D` scene and includes a bounded `FollowCamera2D` plus a `CanvasLayer` HUD marker.

`res://scenes/validation/collision_playground.tscn` instantiates the player inside the walkable-world contract and demonstrates solid boundaries, obstacles, and a non-blocking exit.

Headless behavior coverage lives in:

- `res://tests/godot/player_controller_2d_test.gd`
- `res://tests/godot/follow_camera_2d_test.gd`
- `res://tests/godot/world_scene_contract_test.gd`

The blocking gate is `bash scripts/validate-pr.sh`. Temporary placeholder-atlas conventions remain in `bash scripts/validate-advisory.sh` and do not block normal pull requests.