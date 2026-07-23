extends SceneTree

const COLLISION_PLAYGROUND_PATH: String = "res://scenes/validation/collision_playground.tscn"
const PLAYER_START_PATH: NodePath = NodePath("SpawnPoints/PlayerStart")
const PLAYER_PATH: NodePath = NodePath("Player")
const NORTH_DOOR_PATH: NodePath = NodePath("Exits/NorthDoor")
const WORLD_SCENE_VALIDATOR: Script = preload("res://src/world/world_scene_validator.gd")

var _failures: Array[String] = []

func _init() -> void:
	call_deferred("_run")

func _run() -> void:
	var playground_resource: Resource = load(COLLISION_PLAYGROUND_PATH)
	_expect(playground_resource is PackedScene, "collision playground scene loads")
	var playground_scene: PackedScene = playground_resource as PackedScene
	if playground_scene == null:
		_finish()
		return

	var playground: Node2D = playground_scene.instantiate() as Node2D
	_expect(playground != null, "collision playground instantiates as Node2D")
	if playground == null:
		_finish()
		return

	root.add_child(playground)
	await physics_frame

	var contract_failures: Array[String] = WORLD_SCENE_VALIDATOR.validate_world_scene(playground)
	for failure: String in contract_failures:
		_failures.append(failure)

	var player_start: Marker2D = playground.get_node_or_null(PLAYER_START_PATH) as Marker2D
	var player: CharacterBody2D = playground.get_node_or_null(PLAYER_PATH) as CharacterBody2D
	var north_door: Area2D = playground.get_node_or_null(NORTH_DOOR_PATH) as Area2D
	_expect(player_start != null, "collision playground has a PlayerStart marker")
	_expect(player != null, "collision playground has a player")
	_expect(north_door != null, "collision playground has a north door exit")
	if player_start == null or player == null or north_door == null:
		playground.queue_free()
		_finish()
		return

	player.set("input_enabled", false)
	player.global_position = player_start.global_position
	await physics_frame

	await _move_player_for(player, Vector2.RIGHT, 1.0)
	_expect(player.global_position.x < 62.0, "player cannot pass through the wall segment")

	player.global_position = player_start.global_position
	await physics_frame
	await _move_player_for(player, Vector2.DOWN, 1.0)
	_expect(player.global_position.y < 36.0, "player cannot pass through furniture")

	player.global_position = player_start.global_position
	await physics_frame
	await _move_player_for(player, Vector2.LEFT, 2.0)
	_expect(player.global_position.x > -156.0, "player cannot pass through map boundary")

	player.global_position = player_start.global_position
	await physics_frame
	await _move_player_for(player, Vector2.UP, 0.9)
	_expect(player.global_position.y < -118.0, "walkable door path remains traversable")
	_expect(north_door.get_overlapping_bodies().has(player), "exit sensor detects the player without blocking travel")

	playground.queue_free()
	_finish()

func _move_player_for(player: CharacterBody2D, direction: Vector2, seconds: float) -> void:
	var frame_count: int = maxi(1, ceili(seconds * 60.0))
	var movement_speed: float = float(player.get("movement_speed"))
	for _frame_index: int in range(frame_count):
		player.velocity = direction.normalized() * movement_speed
		player.move_and_slide()
		await physics_frame
	player.velocity = Vector2.ZERO

func _finish() -> void:
	if _failures.is_empty():
		print("world_scene_contract_test: PASS")
		quit(0)
	else:
		for failure: String in _failures:
			push_error(failure)
		quit(1)

func _expect(condition: bool, message: String) -> void:
	if not condition:
		_failures.append(message)
