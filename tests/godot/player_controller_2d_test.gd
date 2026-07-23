extends SceneTree

const SCENE_PATH: String = "res://scenes/actors/player.tscn"
const VALIDATION_SCENE_PATH: String = "res://scenes/validation/player_movement_validation.tscn"
const PLAYER_SCRIPT_PATH: String = "res://src/player/player_controller_2d.gd"
const PLAYER_MOVE_LEFT: StringName = &"player_move_left"
const PLAYER_MOVE_RIGHT: StringName = &"player_move_right"
const PLAYER_MOVE_UP: StringName = &"player_move_up"
const PLAYER_MOVE_DOWN: StringName = &"player_move_down"
const PLAYER_INTERACT: StringName = &"player_interact"
const PLAYER_CANCEL: StringName = &"player_cancel"
const PLAYER_RUN: StringName = &"player_run"
const REQUIRED_ANIMATIONS: Array[StringName] = [
	&"idle_down", &"idle_up", &"idle_left", &"idle_right",
	&"walk_down", &"walk_up", &"walk_left", &"walk_right",
]

var _failures: Array[String] = []

func _init() -> void:
	call_deferred("_run")

func _run() -> void:
	_expect_required_input_map()
	var packed_resource: Resource = load(SCENE_PATH)
	_expect(packed_resource is PackedScene, "player scene loads")
	if not (packed_resource is PackedScene):
		_finish()
		return

	var player: CharacterBody2D = (packed_resource as PackedScene).instantiate() as CharacterBody2D
	_expect(player != null, "player scene root is CharacterBody2D")
	if player == null:
		_finish()
		return

	var player_script: Script = player.get_script() as Script
	_expect(player_script != null and player_script.resource_path == PLAYER_SCRIPT_PATH, "player scene root uses player controller script")
	root.add_child(player)
	await process_frame

	_expect(player.get_node_or_null("CollisionShape2D") is CollisionShape2D, "player has a collision shape")
	var animated_sprite: AnimatedSprite2D = player.get_node_or_null("PlayerAnimatedSprite") as AnimatedSprite2D
	_expect(animated_sprite != null, "player has a directional animated sprite")
	if animated_sprite != null:
		_expect(animated_sprite.sprite_frames != null, "directional animated sprite has sprite frames")
		if animated_sprite.sprite_frames != null:
			for animation_name: StringName in REQUIRED_ANIMATIONS:
				_expect(animated_sprite.sprite_frames.has_animation(animation_name), "player animation exists: %s" % animation_name)

	var movement_speed: float = float(player.get("movement_speed"))
	_expect(movement_speed > 0.0, "movement speed is configurable and positive")
	_expect(player.call("get_facing_animation_direction") == &"down", "player starts facing down")
	_expect(player.call("get_current_animation_name") == &"idle_down", "player starts in idle down animation")

	player.call("apply_movement_input", Vector2.RIGHT)
	_expect(is_equal_approx(player.velocity.length(), movement_speed), "cardinal movement uses configured speed")
	_expect(player.call("get_current_animation_name") == &"walk_right", "right movement selects walk right animation")

	player.call("apply_movement_input", Vector2(1.0, 1.0))
	_expect(is_equal_approx(player.velocity.length(), movement_speed), "diagonal movement is normalized")

	player.call("apply_movement_input", Vector2.ZERO)
	_expect(player.velocity.is_zero_approx(), "idle input clears velocity")
	_expect(player.call("get_current_animation_name") == &"idle_down", "idle preserves last cardinal direction")

	var validation_resource: Resource = load(VALIDATION_SCENE_PATH)
	_expect(validation_resource is PackedScene, "player validation scene loads")
	player.queue_free()
	_finish()

func _expect_required_input_map() -> void:
	for action: StringName in [PLAYER_MOVE_LEFT, PLAYER_MOVE_RIGHT, PLAYER_MOVE_UP, PLAYER_MOVE_DOWN, PLAYER_INTERACT, PLAYER_CANCEL, PLAYER_RUN]:
		_expect(InputMap.has_action(action), "input action exists: %s" % action)

func _expect(condition: bool, message: String) -> void:
	if not condition:
		_failures.append(message)

func _finish() -> void:
	if _failures.is_empty():
		print("player_controller_2d_test: PASS")
		quit(0)
		return
	for failure: String in _failures:
		push_error(failure)
	quit(1)
