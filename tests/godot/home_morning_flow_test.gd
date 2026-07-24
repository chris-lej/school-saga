extends SceneTree

const SCENE_PATH: String = "res://scenes/locations/home_morning.tscn"
const NEIGHBORHOOD_SCENE_PATH: String = "res://scenes/locations/neighborhood_to_school.tscn"
const SAVE_PATH: String = "user://save_slot_1.json"

var _failures: Array[String] = []

func _init() -> void:
	call_deferred("_run")

func _run() -> void:
	if FileAccess.file_exists(SAVE_PATH):
		DirAccess.remove_absolute(ProjectSettings.globalize_path(SAVE_PATH))

	var packed_resource: Resource = load(SCENE_PATH)
	_expect(packed_resource is PackedScene, "home morning scene loads")
	var packed_scene: PackedScene = packed_resource as PackedScene
	_expect(packed_scene != null, "home morning scene loads")
	if packed_scene == null:
		_finish()
		return

	var scene: Control = packed_scene.instantiate() as Control
	_expect(scene != null, "home morning scene root is a Control")
	if scene == null:
		_finish()
		return

	root.add_child(scene)
	await process_frame

	_expect(_has_label(scene, "Primeira manha"), "character entry heading is visible")
	_expect(_has_button(scene, "Open the window"), "character entry can continue")

	var name_input: LineEdit = _find_line_edit(scene)
	_expect(name_input != null, "character entry exposes a name field")
	if name_input != null:
		name_input.text = "Ana"
	_press_button(scene, "Open the window")
	await process_frame

	_expect(_has_label_containing(scene, "Ana stands in the soft morning light"), "bedroom uses entered name")
	_expect(_has_label_containing(scene, "The curtain is thin enough"), "bedroom observations are shown")
	_expect(_has_button(scene, "Go to the kitchen"), "bedroom can advance to breakfast")

	_press_button(scene, "Go to the kitchen")
	await process_frame

	_expect(_has_label(scene, "Kitchen"), "breakfast scene is visible")
	_expect(_has_button(scene, "Pao com manteiga"), "bread breakfast choice is available")
	_expect(_has_button(scene, "Banana from the fruit bowl"), "banana breakfast choice is available")
	_expect(_has_button(scene, "Leave the plate alone"), "skip breakfast choice is available")

	_press_button(scene, "Banana from the fruit bowl")
	await process_frame

	_expect(_has_label(scene, "Neighborhood threshold"), "threshold scene is visible")
	_expect(_has_label_containing(scene, "peel's green smell"), "threshold reflects the selected breakfast")
	_expect(_has_label_containing(scene, "The gate clicks shut behind you"), "threshold observations are shown")
	_expect(_has_button(scene, "Save this morning"), "threshold exposes save action")
	_expect(_has_button(scene, "Step into Rua do Monte"), "threshold exposes neighborhood transition")
	_expect(load(NEIGHBORHOOD_SCENE_PATH) is PackedScene, "neighborhood transition target loads")

	_press_button(scene, "Save this morning")
	await process_frame

	_expect(_has_label(scene, "The morning settles into memory."), "save feedback is shown")

	var save_service: Node = root.get_node_or_null("/root/SaveService")
	_expect(save_service != null, "SaveService autoload is available")
	if save_service != null:
		var save_state: Dictionary = save_service.load_game(SAVE_PATH)
		var flags: Dictionary = save_state.get("flags", {})
		var memory_log: Array = save_state.get("memory_log", [])
		_expect(save_state.get("current_scene", "") == SCENE_PATH, "saved scene points to home morning")
		_expect(flags.get("breakfast_choice", "") == "banana", "saved flags keep breakfast choice")
		_expect(memory_log.size() == 1, "saved memory log records opening morning")

	_finish()

func _finish() -> void:
	if _failures.is_empty():
		print("home_morning_flow_test: PASS")
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

func _find_line_edit(root_node: Node) -> LineEdit:
	if root_node is LineEdit:
		return root_node
	for child: Node in root_node.get_children():
		var found: LineEdit = _find_line_edit(child)
		if found != null:
			return found
	return null

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
