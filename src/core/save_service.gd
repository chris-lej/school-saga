extends Node

const CURRENT_SAVE_VERSION: int = 1
const DEFAULT_SAVE_PATH: String = "user://save_slot_1.json"

signal save_completed(path: String)
signal save_failed(path: String, reason: String)
signal load_completed(path: String)
signal load_failed(path: String, reason: String)

func new_save_state() -> Dictionary:
	return {
		"save_version": CURRENT_SAVE_VERSION,
		"current_scene": "",
		"flags": {},
		"memory_log": []
	}

func save_game(state: Dictionary, path: String = DEFAULT_SAVE_PATH) -> bool:
	var save_state: Dictionary = state.duplicate(true)
	save_state["save_version"] = CURRENT_SAVE_VERSION

	var file: FileAccess = FileAccess.open(path, FileAccess.WRITE)
	if file == null:
		save_failed.emit(path, "Unable to open save file for writing.")
		return false

	file.store_string(JSON.stringify(save_state, "\t"))
	save_completed.emit(path)
	return true

func load_game(path: String = DEFAULT_SAVE_PATH) -> Dictionary:
	if not FileAccess.file_exists(path):
		load_failed.emit(path, "Save file does not exist.")
		return {}

	var file: FileAccess = FileAccess.open(path, FileAccess.READ)
	if file == null:
		load_failed.emit(path, "Unable to open save file for reading.")
		return {}

	var parser: JSON = JSON.new()
	var error_code: int = parser.parse(file.get_as_text())
	if error_code != OK:
		load_failed.emit(path, "Save file is not valid JSON.")
		return {}

	var parsed_data: Variant = parser.data
	if not (parsed_data is Dictionary):
		load_failed.emit(path, "Save file root is not an object.")
		return {}

	var save_state: Dictionary = parsed_data
	if not save_state.has("save_version"):
		load_failed.emit(path, "Save file is missing a version.")
		return {}

	if int(save_state["save_version"]) != CURRENT_SAVE_VERSION:
		load_failed.emit(path, "Save file version is not supported.")
		return {}

	load_completed.emit(path)
	return save_state
