extends Camera2D
class_name FollowCamera2D

@export var target_path: NodePath
@export var world_bounds: Rect2 = Rect2(Vector2.ZERO, Vector2(320.0, 180.0))
@export var follow_zoom: Vector2 = Vector2.ONE
@export var follow_smoothing_enabled: bool = true
@export_range(0.1, 60.0, 0.1, "or_greater") var follow_smoothing_speed: float = 10.0
@export var dead_zone_size: Vector2 = Vector2(24.0, 16.0)
@export var viewport_size_override: Vector2 = Vector2.ZERO

var _target: Node2D

func _ready() -> void:
	zoom = follow_zoom
	_target = get_node_or_null(target_path) as Node2D
	_apply_camera_limits()
	if _target != null:
		global_position = get_framed_position_for_viewport(
			_target.global_position,
			global_position,
			get_viewport_world_size()
		)

func _process(delta: float) -> void:
	if _target == null:
		_target = get_node_or_null(target_path) as Node2D
	if _target == null:
		return

	var target_position: Vector2 = get_framed_position_for_viewport(
		_target.global_position,
		global_position,
		get_viewport_world_size()
	)
	if follow_smoothing_enabled:
		var interpolation_weight: float = 1.0 - exp(-follow_smoothing_speed * delta)
		global_position = global_position.lerp(target_position, interpolation_weight)
	else:
		global_position = target_position

func configure_bounds(bounds: Rect2) -> void:
	world_bounds = bounds
	_apply_camera_limits()

func get_viewport_world_size() -> Vector2:
	if viewport_size_override.x > 0.0 and viewport_size_override.y > 0.0:
		return viewport_size_override / zoom

	var viewport_size: Vector2 = get_viewport_rect().size
	return Vector2(viewport_size.x / zoom.x, viewport_size.y / zoom.y)

func get_framed_position_for_viewport(
	target_position: Vector2,
	current_position: Vector2,
	viewport_world_size: Vector2
) -> Vector2:
	var desired_position: Vector2 = _apply_dead_zone(target_position, current_position)
	return _clamp_to_world_bounds(desired_position, viewport_world_size)

func _apply_dead_zone(target_position: Vector2, current_position: Vector2) -> Vector2:
	if dead_zone_size.x <= 0.0 and dead_zone_size.y <= 0.0:
		return target_position

	var half_dead_zone: Vector2 = dead_zone_size * 0.5
	var desired_position: Vector2 = current_position

	if dead_zone_size.x <= 0.0:
		desired_position.x = target_position.x
	elif target_position.x < current_position.x - half_dead_zone.x:
		desired_position.x = target_position.x + half_dead_zone.x
	elif target_position.x > current_position.x + half_dead_zone.x:
		desired_position.x = target_position.x - half_dead_zone.x

	if dead_zone_size.y <= 0.0:
		desired_position.y = target_position.y
	elif target_position.y < current_position.y - half_dead_zone.y:
		desired_position.y = target_position.y + half_dead_zone.y
	elif target_position.y > current_position.y + half_dead_zone.y:
		desired_position.y = target_position.y - half_dead_zone.y

	return desired_position

func _clamp_to_world_bounds(desired_position: Vector2, viewport_world_size: Vector2) -> Vector2:
	var framed_position: Vector2 = desired_position

	if world_bounds.size.x <= viewport_world_size.x:
		framed_position.x = world_bounds.position.x + (world_bounds.size.x * 0.5)
	else:
		var horizontal_margin: float = viewport_world_size.x * 0.5
		framed_position.x = clampf(
			desired_position.x,
			world_bounds.position.x + horizontal_margin,
			world_bounds.end.x - horizontal_margin
		)

	if world_bounds.size.y <= viewport_world_size.y:
		framed_position.y = world_bounds.position.y + (world_bounds.size.y * 0.5)
	else:
		var vertical_margin: float = viewport_world_size.y * 0.5
		framed_position.y = clampf(
			desired_position.y,
			world_bounds.position.y + vertical_margin,
			world_bounds.end.y - vertical_margin
		)

	return framed_position

func _apply_camera_limits() -> void:
	limit_left = roundi(world_bounds.position.x)
	limit_top = roundi(world_bounds.position.y)
	limit_right = roundi(world_bounds.end.x)
	limit_bottom = roundi(world_bounds.end.y)
