extends Node2D
class_name WalkableWorldScene

const WORLD_SCENE_VALIDATOR: Script = preload("res://src/world/world_scene_validator.gd")

@export var validate_contract_on_ready: bool = true

func _ready() -> void:
	if not validate_contract_on_ready:
		return
	if not OS.is_debug_build():
		return

	var failures: Array[String] = WORLD_SCENE_VALIDATOR.validate_world_scene(self)
	for failure: String in failures:
		push_error("%s: %s" % [name, failure])
