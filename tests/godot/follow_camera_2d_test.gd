extends SceneTree

const CAMERA_SCRIPT_PATH: String = "res://src/camera/follow_camera_2d.gd"
const VALIDATION_SCENE_PATH: String = "res://scenes/validation/player_movement_validation.tscn"
const CAMERA_SCRIPT: Script = preload("res://src/camera/follow_camera_2d.gd")

var _failures: Array[String] = []

func _init() -> void:
	call_deferred("_run")

func _run() -> void:
	var camera: Camera2D = CAMERA_SCRIPT.new() as Camera2D
	_expect(camera != null, "follow camera script instantiates a Camera2D")
	if camera == null:
		_finish()
		return

	root.add_child(camera)
	camera.set("dead_zone_size", Vector2.ZERO)
	camera.set("world_bounds", Rect2(Vector2.ZERO, Vector2(640.0, 360.0)))
	camera.set("follow_zoom", Vector2.ONE)
	camera.set("viewport_size_override", Vector2(320.0, 180.0))
	await process_frame

	var centered_position: Vector2 = camera.call(
		"get_framed_position_for_viewport",
		Vector2(320.0, 180.0),
		Vector2.ZERO,
		Vector2(320.0, 180.0)
	)
	_expect(centered_position.is_equal_approx(Vector2(320.0, 180.0)), "camera centers on target inside bounds")

	var clamped_top_left: Vector2 = camera.call(
		"get_framed_position_for_viewport",
		Vector2.ZERO,
		Vector2.ZERO,
		Vector2(320.0, 180.0)
	)
	_expect(clamped_top_left.is_equal_approx(Vector2(160.0, 90.0)), "camera clamps to top-left world edge")

	var clamped_bottom_right: Vector2 = camera.call(
		"get_framed_position_for_viewport",
		Vector2(640.0, 360.0),
		Vector2(320.0, 180.0),
		Vector2(320.0, 180.0)
	)
	_expect(clamped_bottom_right.is_equal_approx(Vector2(480.0, 270.0)), "camera clamps to bottom-right world edge")

	camera.set("world_bounds", Rect2(Vector2(100.0, 40.0), Vector2(120.0, 80.0)))
	var small_room_position: Vector2 = camera.call(
		"get_framed_position_for_viewport",
		Vector2(180.0, 80.0),
		Vector2.ZERO,
		Vector2(320.0, 180.0)
	)
	_expect(small_room_position.is_equal_approx(Vector2(160.0, 80.0)), "small rooms center inside larger viewport")

	camera.set("world_bounds", Rect2(Vector2.ZERO, Vector2(640.0, 360.0)))
	camera.set("dead_zone_size", Vector2(80.0, 60.0))
	var dead_zone_position: Vector2 = camera.call(
		"get_framed_position_for_viewport",
		Vector2(330.0, 190.0),
		Vector2(320.0, 180.0),
		Vector2(320.0, 180.0)
	)
	_expect(dead_zone_position.is_equal_approx(Vector2(320.0, 180.0)), "dead zone holds camera while target stays inside")

	var validation_resource: Resource = load(VALIDATION_SCENE_PATH)
	_expect(validation_resource is PackedScene, "player movement validation scene loads")
	if validation_resource is PackedScene:
		var validation_scene: Node = (validation_resource as PackedScene).instantiate()
		var validation_camera: Camera2D = validation_scene.get_node_or_null("Camera2D") as Camera2D
		_expect(validation_camera != null, "validation scene has a camera")
		if validation_camera != null:
			var script: Script = validation_camera.get_script() as Script
			_expect(script != null and script.resource_path == CAMERA_SCRIPT_PATH, "validation camera uses follow camera script")
			_expect(validation_camera.get("target_path") == NodePath("../Player"), "validation camera targets the player")
			_expect((validation_camera.get("world_bounds") as Rect2).size.x > 0.0, "validation camera has configured map bounds")
		_expect(validation_scene.get_node_or_null("HUDLayer") is CanvasLayer, "validation HUD is on an independent CanvasLayer")
		validation_scene.queue_free()

	camera.queue_free()
	_finish()

func _finish() -> void:
	if _failures.is_empty():
		print("follow_camera_2d_test: PASS")
		quit(0)
	else:
		for failure: String in _failures:
			push_error(failure)
		quit(1)

func _expect(condition: bool, message: String) -> void:
	if not condition:
		_failures.append(message)
