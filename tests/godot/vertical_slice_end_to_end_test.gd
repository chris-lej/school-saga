extends SceneTree

const HOME_SCENE: String = "res://scenes/locations/home_morning.tscn"
const NEIGHBORHOOD_SCENE: String = "res://scenes/locations/neighborhood_to_school.tscn"
const SCHOOL_SCENE: String = "res://scenes/locations/school_first_day.tscn"
const RETURN_HOME_SCENE: String = "res://scenes/locations/return_home.tscn"
const SAVE_PATH: String = "user://save_slot_1.json"

var _failures: Array[String] = []

func _init() -> void:
	call_deferred("_run")

func _run() -> void:
	if FileAccess.file_exists(SAVE_PATH):
		DirAccess.remove_absolute(ProjectSettings.globalize_path(SAVE_PATH))

	var home := _instantiate_control(HOME_SCENE, "home morning scene")
	if home == null:
		_finish()
		return
	root.add_child(home)
	await process_frame
	_press_button(home, "Open the window")
	await process_frame
	_press_button(home, "Go to the kitchen")
	await process_frame
	_press_button(home, "Banana from the fruit bowl")
	await process_frame
	_expect(_has_button(home, "Step into Rua do Monte"), "home flow reaches neighborhood transition action")
	home.queue_free()
	await process_frame

	var neighborhood := _instantiate_control(NEIGHBORHOOD_SCENE, "neighborhood transition scene")
	if neighborhood == null:
		_finish()
		return
	root.add_child(neighborhood)
	await process_frame
	_expect(_has_button(neighborhood, "Continue to school"), "neighborhood flow exposes school transition")
	neighborhood.queue_free()
	await process_frame

	var school := _instantiate_control(SCHOOL_SCENE, "school first-day scene")
	if school == null:
		_finish()
		return
	root.add_child(school)
	await process_frame
	_press_button(school, "Follow the first bell")
	await process_frame
	_press_button(school, "Window seat beside the faded curtain")
	await process_frame
	_press_button(school, "Drift toward basketball")
	await process_frame
	_press_button(school, "Join when the ball rolls over")
	await process_frame
	_press_button(school, "Linger by the canteen shade")
	await process_frame
	_expect(_has_button(school, "Head home after school"), "school flow exposes return-home action after rumor")
	_press_button(school, "Head home after school")
	await process_frame

	var save_service: Node = root.get_node_or_null("/root/SaveService")
	_expect(save_service != null, "SaveService autoload is available")
	if save_service != null:
		var school_state: Dictionary = save_service.load_game(SAVE_PATH)
		_expect(school_state.get("current_scene", "") == RETURN_HOME_SCENE, "school handoff saves return-home scene")
		var flags: Dictionary = school_state.get("flags", {})
		_expect(flags.get("class_seat", "") == "window", "route preserves seating choice")
		_expect(flags.get("recess_basketball", "") == "join", "route preserves basketball choice")
		_expect(flags.get("rumor_status", "") == "unresolved", "route preserves unresolved rumor")
	school.queue_free()
	await process_frame

	var return_home := _instantiate_control(RETURN_HOME_SCENE, "return-home scene")
	if return_home == null:
		_finish()
		return
	root.add_child(return_home)
	await process_frame
	_expect(_has_button(return_home, "Save completed day"), "return-home flow can persist completion")
	_press_button(return_home, "Save completed day")
	await process_frame

	if save_service != null:
		var completed_state: Dictionary = save_service.load_game(SAVE_PATH)
		var completed_flags: Dictionary = completed_state.get("flags", {})
		var memory_log: Array = completed_state.get("memory_log", [])
		_expect(bool(completed_flags.get("first_day_complete", false)), "completed route records first-day completion")
		_expect(_memory_log_has(memory_log, "return_home_first_day"), "completed route appends return-home memory")

	return_home.queue_free()
	await process_frame
	_finish()

func _instantiate_control(path: String, label: String) -> Control:
	var resource: Resource = load(path)
	_expect(resource is PackedScene, "%s loads" % label)
	if not resource is PackedScene:
		return null
	var scene: Control = (resource as PackedScene).instantiate() as Control
	_expect(scene != null, "%s root is a Control" % label)
	return scene

func _memory_log_has(memory_log: Array, id: String) -> bool:
	for entry: Variant in memory_log:
		if entry is Dictionary and str(entry.get("id", "")) == id:
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

func _expect(condition: bool, message: String) -> void:
	if not condition:
		_failures.append(message)

func _finish() -> void:
	if _failures.is_empty():
		print("vertical_slice_end_to_end_test: PASS")
		quit(0)
	else:
		for failure: String in _failures:
			push_error(failure)
		quit(1)
