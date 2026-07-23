extends RefCounted
class_name WorldSceneValidator

const WORLD_COLLISION_LAYERS: Script = preload("res://src/world/world_collision_layers.gd")
const REQUIRED_ROOT_CHILDREN: Array[StringName] = [
	&"VisualLayers",
	&"Collision",
	&"Interactables",
	&"SpawnPoints",
	&"Exits",
	&"ForegroundOcclusion",
	&"NavigationMarkers",
]

static func validate_world_scene(scene_root: Node) -> Array[String]:
	var failures: Array[String] = []
	if scene_root == null:
		return ["world scene root is missing"]
	if not scene_root is Node2D:
		failures.append("world scene root must be a Node2D")

	for child_name: StringName in REQUIRED_ROOT_CHILDREN:
		if scene_root.get_node_or_null(NodePath(child_name)) == null:
			failures.append("world scene is missing required child: %s" % child_name)

	_validate_player(scene_root, failures)
	_validate_spawn_points(scene_root, failures)
	_validate_solid_collisions(scene_root, failures)
	_validate_exit_sensors(scene_root, failures)
	return failures

static func _validate_player(scene_root: Node, failures: Array[String]) -> void:
	var player: CharacterBody2D = scene_root.get_node_or_null("Player") as CharacterBody2D
	if player == null:
		failures.append("world scene must instantiate a CharacterBody2D named Player")
		return
	if player.collision_layer != WORLD_COLLISION_LAYERS.PLAYER:
		failures.append("Player must use the player collision layer")
	if player.collision_mask != WORLD_COLLISION_LAYERS.PLAYER_COLLISION_MASK:
		failures.append("Player must collide only with world solids")
	var shape: CollisionShape2D = player.get_node_or_null("CollisionShape2D") as CollisionShape2D
	if shape == null or shape.disabled or shape.shape == null:
		failures.append("Player must have an enabled CollisionShape2D")

static func _validate_spawn_points(scene_root: Node, failures: Array[String]) -> void:
	var spawn_points: Node = scene_root.get_node_or_null("SpawnPoints")
	if spawn_points == null:
		return
	var player_start: Marker2D = spawn_points.get_node_or_null("PlayerStart") as Marker2D
	if player_start == null:
		failures.append("SpawnPoints must include a Marker2D named PlayerStart")

static func _validate_solid_collisions(scene_root: Node, failures: Array[String]) -> void:
	var collision_root: Node = scene_root.get_node_or_null("Collision")
	if collision_root == null:
		return
	var solid_count: int = 0
	for node: Node in _collect_descendants(collision_root):
		var body: StaticBody2D = node as StaticBody2D
		if body == null:
			continue
		solid_count += 1
		if body.collision_layer != WORLD_COLLISION_LAYERS.WORLD_SOLID:
			failures.append("%s must use the world solid collision layer" % body.name)
		if body.collision_mask != WORLD_COLLISION_LAYERS.WORLD_SOLID_COLLISION_MASK:
			failures.append("%s must collide with the player layer" % body.name)
		if not _has_enabled_shape(body):
			failures.append("%s must have at least one enabled CollisionShape2D" % body.name)
	if solid_count == 0:
		failures.append("Collision must include at least one StaticBody2D obstacle or boundary")

static func _validate_exit_sensors(scene_root: Node, failures: Array[String]) -> void:
	var exits_root: Node = scene_root.get_node_or_null("Exits")
	if exits_root == null:
		return
	var exit_count: int = 0
	for node: Node in _collect_descendants(exits_root):
		var exit_area: Area2D = node as Area2D
		if exit_area == null:
			continue
		exit_count += 1
		if exit_area.collision_layer != WORLD_COLLISION_LAYERS.EXIT:
			failures.append("%s must use the exit sensor collision layer" % exit_area.name)
		if exit_area.collision_mask != WORLD_COLLISION_LAYERS.SENSOR_COLLISION_MASK:
			failures.append("%s must monitor the player layer" % exit_area.name)
		if not _has_enabled_shape(exit_area):
			failures.append("%s must have at least one enabled CollisionShape2D" % exit_area.name)
	if exit_count == 0:
		failures.append("Exits must include at least one Area2D exit sensor")

static func _has_enabled_shape(collision_object: CollisionObject2D) -> bool:
	for child: Node in collision_object.get_children():
		var shape: CollisionShape2D = child as CollisionShape2D
		if shape != null and not shape.disabled and shape.shape != null:
			return true
	return false

static func _collect_descendants(root_node: Node) -> Array[Node]:
	var nodes: Array[Node] = []
	for child: Node in root_node.get_children():
		nodes.append(child)
		nodes.append_array(_collect_descendants(child))
	return nodes
