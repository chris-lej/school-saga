extends SceneTree

const SCENE_PATH: String = "res://scenes/locations/school_first_day.tscn"
const SAVE_PATH: String = "user://save_slot_1.json"

var _failures: Array[String] = []

func _init() -> void:
	call_deferred("_run")

func _run() -> void:
	if FileAccess.file_exists(SAVE_PATH):
		DirAccess.remove_absolute(ProjectSettings.globalize_path(SAVE_PATH))

	var packed_resource: Resource = load(SCENE_PATH)
	_expect(packed_resource is PackedScene, "school first-day scene loads")
	var packed_scene: PackedScene = packed_resource as PackedScene
	_expect(packed_scene != null, "school first-day scene loads")
	if packed_scene == null:
		_finish()
		return

	var scene: Control = packed_scene.instantiate() as Control
	_expect(scene != null, "school first-day scene root is a Control")
	if scene == null:
		_finish()
		return

	root.add_child(scene)
	await process_frame

	var initial_relationships: Dictionary = scene.get_relationship_debug_snapshot()
	var initial_player_relationships: Dictionary = initial_relationships.get("player", {})
	_expect(initial_player_relationships.has("bia"), "internal relationship state exists for Bia")
	_expect(initial_player_relationships.has("marina"), "internal relationship state exists for Marina")
	_expect(int(initial_player_relationships.get("marina", {}).get("familiarity", -1)) == 0, "Marina relationship starts neutral internally")

	_expect(_has_label(scene, "Colegio Monte Araucaria"), "school heading is visible on arrival")
	_expect(_has_label_containing(scene, "The courtyard is louder than the street"), "courtyard is already active")
	_expect(_has_label(scene, "Courtyard routines"), "courtyard routines are visible")
	_expect(_has_label_containing(scene, "Bia: yellow hair clip"), "Bia has visual identity and routine")
	_expect(_has_label_containing(scene, "Caio: rolled uniform sleeves"), "Caio has visual identity and routine")
	_expect(_has_label_containing(scene, "Luan: oversized glasses"), "Luan has visual identity and routine")
	_expect(_has_label_containing(scene, "Marina: braided ribbon"), "Marina has visual identity and routine")
	_expect(_has_button(scene, "Follow the first bell"), "courtyard can advance to class")

	_press_button(scene, "Follow the first bell")
	await process_frame

	_expect(_has_label(scene, "First class"), "classroom scene is visible")
	_expect(_has_button(scene, "Front row near the teacher's desk"), "front seating choice is available")
	_expect(_has_button(scene, "Window seat beside the faded curtain"), "window seating choice is available")
	_expect(_has_button(scene, "Middle row between two conversations"), "middle seating choice is available")
	_expect(_has_button(scene, "Back row near the loose fan switch"), "back seating choice is available")

	_press_button(scene, "Window seat beside the faded curtain")
	await process_frame

	_expect(_has_label(scene, "Roll call"), "shared-experience scene is visible")
	_expect(_has_label_containing(scene, "Marina catches the curtain"), "selected seating creates shared consequence")
	_expect(_has_label(scene, "Marina stays part of the moment without making a speech of it."), "shared consequence names the involved classmate observationally")
	_expect(_has_label(scene, "Recess drift"), "relationship feedback is presented through later behavior")
	_expect(_has_label_containing(scene, "Marina waits a little longer near the classroom door"), "player-facing relationship feedback uses availability and proximity")
	_expect(_has_label_containing(scene, "Bia rescues a sticker from Caio's bottle-cap goal line"), "NPC-to-NPC social change appears without player involvement")
	_expect(not _has_label_containing(scene, "friendship"), "normal relationship feedback avoids friendship meter language")
	_expect(_has_button(scene, "Drift toward basketball"), "class flow can continue into recess basketball")

	var changed_relationships: Dictionary = scene.get_relationship_debug_snapshot()
	var changed_player_relationships: Dictionary = changed_relationships.get("player", {})
	var marina_relationship: Dictionary = changed_player_relationships.get("marina", {})
	var npc_relationships: Dictionary = changed_relationships.get("npc", {})
	var bia_caio_relationship: Dictionary = npc_relationships.get("bia:caio", {})
	_expect(int(marina_relationship.get("familiarity", 0)) == 1, "shared experience changes Marina familiarity internally")
	_expect(int(marina_relationship.get("trust", 0)) == 1, "shared experience changes Marina trust internally")
	_expect(str(marina_relationship.get("tone", "")) == "quietly warmer", "shared experience changes Marina tone internally")
	_expect(int(bia_caio_relationship.get("tension", 0)) == 1, "independent NPC-to-NPC change updates internal state")

	_press_button(scene, "Drift toward basketball")
	await process_frame

	_expect(_has_label(scene, "Recess basketball"), "basketball interaction is visible")
	_expect(_has_label_containing(scene, "three different arguments about who is actually on whose team"), "basketball game feels already in motion")
	_expect(_has_button(scene, "Watch from the low wall"), "player can watch basketball")
	_expect(_has_button(scene, "Join when the ball rolls over"), "player can join basketball")
	_expect(_has_button(scene, "Leave for the canteen shade"), "player can leave basketball")

	_press_button(scene, "Join when the ball rolls over")
	await process_frame

	_expect(_has_label(scene, "The ball keeps moving"), "basketball outcome is visible")
	_expect(_has_label_containing(scene, "half catch, half self-defense"), "joining basketball creates an awkward humorous outcome")
	_expect(_has_label_containing(scene, "Bia shifts her sticker album"), "basketball outcome affects later behavior")
	_expect(_has_label_containing(scene, "Bia's teasing leaves a place inside it"), "relationship effect is expressed through behavior")
	_expect(not _has_label_containing(scene, "points"), "basketball feedback avoids relationship points language")
	_expect(_has_button(scene, "Linger by the canteen shade"), "basketball flow exposes optional rumor observation")
	_expect(_has_button(scene, "Save the recess memory"), "basketball flow exposes save action")

	var basketball_relationships: Dictionary = scene.get_relationship_debug_snapshot()
	var basketball_player_relationships: Dictionary = basketball_relationships.get("player", {})
	var bia_relationship: Dictionary = basketball_player_relationships.get("bia", {})
	_expect(int(bia_relationship.get("familiarity", 0)) == 1, "basketball shared experience changes Bia familiarity internally")
	_expect(str(bia_relationship.get("tone", "")) == "prickly welcome", "basketball shared experience changes Bia tone internally")

	var rumor_debug: Dictionary = scene.get_rumor_debug_snapshot()
	var rumor_source: Dictionary = rumor_debug.get("source", {})
	var reliability_profile: Dictionary = rumor_source.get("reliability_profile", {})
	var truth_possibilities: Array = rumor_debug.get("truth_possibilities", [])
	_expect(str(rumor_source.get("id", "")) == "bia", "rumor source is attached to a known classmate")
	_expect(not str(reliability_profile.get("pattern", "")).is_empty(), "rumor source has a learnable reliability profile")
	_expect(str(rumor_debug.get("state", "")) == "incomplete_or_conditional", "rumor truth state can remain incomplete or conditional")
	_expect(truth_possibilities.has("false"), "rumor data allows false interpretations")
	_expect(truth_possibilities.has("exaggerated"), "rumor data allows exaggerated interpretations")

	_press_button(scene, "Linger by the canteen shade")
	await process_frame

	_expect(_has_label(scene, "Canteen shade"), "rumor observation is visible after lingering")
	_expect(_has_label_containing(scene, "late recess"), "rumor discovery is tied to time")
	_expect(_has_label_containing(scene, "canteen shade beside the corridor"), "rumor discovery is tied to place")
	_expect(_has_label_containing(scene, "little radio song gets clear beside the locked storage room"), "rumor line is overheard")
	_expect(_has_label_containing(scene, "changes 'storage room' to 'the other storage room'"), "source behavior exposes reliability through contradiction")
	_expect(_has_label_containing(scene, "The corridor door stays locked"), "rumor remains unresolved in the slice")
	_expect(_has_label(scene, "Nothing settles before the bell."), "rumor does not resolve before slice end")
	_expect(not _has_label_containing(scene, "objective"), "rumor feedback avoids objective language")
	_expect(not _has_label_containing(scene, "quest"), "rumor feedback avoids quest language")
	_expect(_has_button(scene, "Save the recess memory"), "rumor flow can still save")

	_press_button(scene, "Save the recess memory")
	await process_frame

	_expect(_has_label(scene, "The rumor stays unfinished in memory."), "save feedback preserves unresolved rumor")

	var save_service: Node = root.get_node_or_null("/root/SaveService")
	_expect(save_service != null, "SaveService autoload is available")
	if save_service != null:
		var save_state: Dictionary = save_service.load_game(SAVE_PATH)
		var flags: Dictionary = save_state.get("flags", {})
		var memory_log: Array = save_state.get("memory_log", [])
		var saved_relationships: Dictionary = save_state.get("debug_relationship_state", {})
		_expect(save_state.get("current_scene", "") == SCENE_PATH, "saved scene points to school first day")
		_expect(flags.get("class_seat", "") == "window", "saved flags keep seating choice")
		_expect(flags.get("shared_with", "") == "Marina", "saved flags keep shared classmate")
		_expect(flags.get("independent_social_event", "") == "sticker_goal_argument", "saved flags keep independent social event")
		_expect(flags.get("recess_basketball", "") == "join", "saved flags keep basketball choice")
		_expect(flags.get("rumor", "") == "radio_keychain_storage_room", "saved flags keep discovered rumor")
		_expect(flags.get("rumor_status", "") == "unresolved", "saved flags keep rumor unresolved")
		_expect(memory_log.size() == 4, "saved memory log records first class, independent social event, basketball, and rumor")
		_expect(saved_relationships.has("player"), "debug save data can expose internal relationship state")
		_expect(save_state.has("debug_rumor"), "debug save data can expose authored rumor state")

	_finish()

func _finish() -> void:
	if _failures.is_empty():
		print("school_first_day_flow_test: PASS")
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
