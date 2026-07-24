extends SceneTree

const SCENE_PATH: String = "res://scenes/locations/return_home.tscn"
const SAVE_PATH: String = "user://save_slot_1.json"

var _failures: Array[String] = []

func _init() -> void:
	call_deferred("_run")

func _run() -> void:
	if FileAccess.file_exists(SAVE_PATH):
		DirAccess.remove_absolute(ProjectSettings.globalize_path(SAVE_PATH))

	var save_service: Node = root.get_node_or_null("/root/SaveService")
	_expect(save_service != null, "SaveService autoload is available")
	if save_service == null:
		_finish()
		return

	var initial_state: Dictionary = save_service.new_save_state()
	initial_state["current_scene"] = "res://scenes/locations/school_first_day.tscn"
	initial_state["flags"] = {
		"class_seat": "window",
		"recess_basketball": "join",
		"rumor": "radio_keychain_storage_room",
		"rumor_status": "unresolved"
	}
	initial_state["memory_log"] = [
		{"id": "first_day_class_seat"},
		{"id": "recess_basketball"},
		{"id": "radio_keychain_storage_room"}
	]
	_expect(save_service.save_game(initial_state), "school state can be prepared for return-home validation")

	var packed_resource: Resource = load(SCENE_PATH)
	_expect(packed_resource is PackedScene, "return-home scene loads")
	var packed_scene: PackedScene = packed_resource as PackedScene
	if packed_scene == null:
		_finish()
		return

	var scene: Control = packed_scene.instantiate() as Control
	_expect(scene != null, "return-home scene root is a Control")
	if scene == null:
		_finish()
		return

	root.add_child(scene)
	await process_frame

	_expect(_has_label(scene, "Back home"), "return-home heading is visible")
	_expect(_has_label_containing(scene, "seat you chose"), "return-home summary reflects classroom choice")
	_expect(_has_label_containing(scene, "recess game"), "return-home summary reflects basketball")
	_expect(_has_label_containing(scene, "storage-room rumor"), "return-home summary preserves unresolved rumor")
	_expect(_has_button(scene, "Save the completed first day"), "return-home flow can save completion")
	_expect(_has_button(scene, "Begin another morning"), "return-home flow can restart")

	_press_button(scene, "Save the completed first day")
	await process_frame

	_expect(_has_label(scene, "The whole first day settles into memory."), "completion save feedback is shown")

	var saved_state: Dictionary = save_service.load_game(SAVE_PATH)
	var flags: Dictionary = saved_state.get("flags", {})
	var memory_log: Array = saved_state.get("memory_log", [])
	_expect(saved_state.get("current_scene", "") == SCENE_PATH, "completed save points to return-home scene")
	_expect(flags.get("first_day_complete", false), "completed save marks first day complete")
	_expect(memory_log.size() == 4, "completed save appends return-home memory")
	_expect(str(memory_log[-1].get("id", "")) == "first_day_return_home", "return-home memory is appended last")

	_finish()

func _finish() -> void:
	if _failures.is_empty():
		print("return_home_flow_test: PASS")
		quit(0)
	else:
		for failure: String in _failures:
			push_error(failure)
		quit(1)

func _expect(condition: bool, message: String) -> void:
	if not condition:
		_failures.append(message)

func _has_label(root_node: Node, text: String) -> bool:
	for label: Label in _find_labels(root_node):
		if label.text == text:
			return true
	return false

func _has_label_containing(root_node: Node, text: String) -> bool:
	for label: Label in _find_labels(root_node):
		if label.text.contains(text):
			return true
	return false

func _has_button(root_node: Node, text: String) -> bool:
	return _find_button(root_node, text) != null

func _press_button(root_node: Node, text: String) -> void:
	var button: Button = _find_button(root_node, text)
	_expect(button != null, "button exists before press: %s" % text)
	if button != null:
		button.pressed.emit()

func _find_button(root_node: Node, text: String) -> Button:
	if root_node is Button and root_node.text == text:
		return root_node
	for child: Node in root_node.get_children():
		var found: Button = _find_button(child, text)
		if found != null:
			return found
	return null

func _find_labels(root_node: Node) -> Array[Label]:
	var labels: Array[Label] = []
	if root_node is Label:
		labels.append(root_node)
	for child: Node in root_node.get_children():
		labels.append_array(_find_labels(child))
	return labels
