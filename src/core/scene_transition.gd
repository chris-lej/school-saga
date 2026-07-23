extends Node

signal scene_change_started(scene_path: String)
signal scene_change_failed(scene_path: String, error_code: int)
signal scene_change_completed(scene_path: String)

func change_scene(scene_path: String) -> bool:
	if scene_path.is_empty():
		scene_change_failed.emit(scene_path, ERR_INVALID_PARAMETER)
		return false

	scene_change_started.emit(scene_path)
	var error_code: int = get_tree().change_scene_to_file(scene_path)
	if error_code != OK:
		scene_change_failed.emit(scene_path, error_code)
		return false

	scene_change_completed.emit(scene_path)
	return true

func reload_current_scene() -> bool:
	var current_scene: Node = get_tree().current_scene
	if current_scene == null:
		scene_change_failed.emit("", ERR_DOES_NOT_EXIST)
		return false

	var scene_file_path: String = current_scene.scene_file_path
	if scene_file_path.is_empty():
		scene_change_failed.emit(scene_file_path, ERR_FILE_NOT_FOUND)
		return false

	return change_scene(scene_file_path)
