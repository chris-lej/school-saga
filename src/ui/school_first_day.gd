extends Control

const SCHOOL_DATA_PATH: String = "res://data/school_first_day.json"
const SCENE_PATH: String = "res://scenes/locations/school_first_day.tscn"

var selected_seat_id: String = ""
var selected_basketball_choice_id: String = ""
var shared_experience: Dictionary = {}
var recess_basketball_memory: Dictionary = {}
var discovered_rumor: Dictionary = {}

var _data: Dictionary = {}
var _relationship_state: Dictionary = {}
var _selected_relationship_effect: Dictionary = {}
var _selected_basketball_choice: Dictionary = {}
var _independent_social_event: Dictionary = {}
var _selected_rumor: Dictionary = {}
var _background: ColorRect
var _panel: MarginContainer
var _content: VBoxContainer
var _status_label: Label

func _ready() -> void:
	_data = _load_school_data()
	_relationship_state = _load_relationship_state()
	_build_shell()
	_show_courtyard()

func _load_school_data() -> Dictionary:
	var file: FileAccess = FileAccess.open(SCHOOL_DATA_PATH, FileAccess.READ)
	if file == null:
		push_warning("School first-day data could not be loaded.")
		return {
			"arrival_observations": [],
			"classmates": [],
			"classroom_observations": [],
			"recess_basketball": {},
			"relationships": {},
			"seats": [],
			"rumors": []
		}

	var parsed: Variant = JSON.parse_string(file.get_as_text())
	if parsed is Dictionary:
		return parsed

	push_warning("School first-day data is not a JSON object.")
	return {
		"arrival_observations": [],
		"classmates": [],
		"classroom_observations": [],
		"recess_basketball": {},
		"relationships": {},
		"seats": [],
		"rumors": []
	}

func _load_relationship_state() -> Dictionary:
	var relationship_data: Variant = _data.get("relationships", {})
	if relationship_data is Dictionary:
		return relationship_data.duplicate(true)
	return {
		"player": {},
		"npc": {}
	}

func get_relationship_debug_snapshot() -> Dictionary:
	return _relationship_state.duplicate(true)

func get_rumor_debug_snapshot() -> Dictionary:
	if not _selected_rumor.is_empty():
		return _selected_rumor.duplicate(true)
	return _get_first_rumor()

func _build_shell() -> void:
	_background = ColorRect.new()
	_background.color = Color(0.72, 0.80, 0.74)
	_background.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(_background)

	_panel = MarginContainer.new()
	_panel.set_anchors_preset(Control.PRESET_FULL_RECT)
	_panel.add_theme_constant_override("margin_left", 56)
	_panel.add_theme_constant_override("margin_top", 40)
	_panel.add_theme_constant_override("margin_right", 56)
	_panel.add_theme_constant_override("margin_bottom", 40)
	add_child(_panel)

	_content = VBoxContainer.new()
	_content.alignment = BoxContainer.ALIGNMENT_CENTER
	_content.add_theme_constant_override("separation", 12)
	_panel.add_child(_content)

func _clear_content() -> void:
	for child: Node in _content.get_children():
		child.queue_free()

func _show_courtyard() -> void:
	_clear_content()
	_set_school_light(Color(0.70, 0.82, 0.73))
	_add_heading("Colegio Monte Araucaria")
	for observation: String in _data.get("arrival_observations", []):
		_add_observation(observation)
	_add_subheading("Courtyard routines")
	for classmate: Dictionary in _data.get("classmates", []):
		_add_observation("%s: %s; %s." % [str(classmate.get("name", "")), str(classmate.get("visual_identity", "")), str(classmate.get("routine", ""))])
	var continue_button: Button = _make_button("Follow the first bell")
	continue_button.pressed.connect(_show_classroom)
	_content.add_child(continue_button)

func _show_classroom() -> void:
	_clear_content()
	_set_school_light(Color(0.78, 0.76, 0.66))
	_add_heading("First class")
	for observation: String in _data.get("classroom_observations", []):
		_add_observation(observation)
	_add_subheading("Choose a desk")
	for seat: Dictionary in _data.get("seats", []):
		var seat_button: Button = _make_button(str(seat.get("label", "")))
		seat_button.pressed.connect(_on_seat_selected.bind(seat))
		_content.add_child(seat_button)

func _on_seat_selected(seat: Dictionary) -> void:
	selected_seat_id = str(seat.get("id", ""))
	_selected_relationship_effect = _get_dictionary(seat.get("relationship_effect", {}))
	shared_experience = {
		"seat_id": selected_seat_id,
		"shared_with": str(seat.get("shared_with", "")),
		"consequence": str(seat.get("consequence", ""))
	}
	_apply_player_relationship_effect(_selected_relationship_effect)
	_apply_independent_social_event()
	_show_shared_experience()

func _show_shared_experience() -> void:
	_clear_content()
	_set_school_light(Color(0.84, 0.80, 0.68))
	_add_heading("Roll call")
	_add_observation("The teacher reads names from a sheet softened at the corners. The room answers in uneven voices.")
	_add_observation(str(shared_experience.get("consequence", "")))
	_add_observation("By the time the chalk touches the board, the seat already belongs to a small piece of the morning.")
	_status_label = _add_observation("%s stays part of the moment without making a speech of it." % str(shared_experience.get("shared_with", "")))
	_add_subheading("Recess drift")
	_add_observation(str(_selected_relationship_effect.get("behavior_feedback", "")))
	_add_observation(str(_independent_social_event.get("behavior_feedback", "")))
	_add_relationship_debug_summary()
	var basketball_button: Button = _make_button("Drift toward basketball")
	basketball_button.pressed.connect(_show_basketball)
	_content.add_child(basketball_button)

func _show_basketball() -> void:
	_clear_content()
	_set_school_light(Color(0.82, 0.78, 0.61))
	_add_heading("Recess basketball")
	var basketball_data: Dictionary = _get_dictionary(_data.get("recess_basketball", {}))
	for observation: String in basketball_data.get("setup_observations", []):
		_add_observation(observation)
	_add_subheading("Shared recess")
	for choice: Dictionary in basketball_data.get("choices", []):
		var choice_button: Button = _make_button(str(choice.get("label", "")))
		choice_button.pressed.connect(_on_basketball_choice_selected.bind(choice))
		_content.add_child(choice_button)

func _on_basketball_choice_selected(choice: Dictionary) -> void:
	selected_basketball_choice_id = str(choice.get("id", ""))
	_selected_basketball_choice = _get_dictionary(choice)
	var relationship_effect: Dictionary = _get_dictionary(choice.get("relationship_effect", {}))
	recess_basketball_memory = {
		"choice_id": selected_basketball_choice_id,
		"outcome": str(choice.get("outcome", "")),
		"later_behavior": str(choice.get("later_behavior", ""))
	}
	_apply_player_relationship_effect(relationship_effect)
	_show_basketball_outcome()

func _show_basketball_outcome() -> void:
	_clear_content()
	_set_school_light(Color(0.86, 0.75, 0.55))
	_add_heading("The ball keeps moving")
	_add_observation(str(recess_basketball_memory.get("outcome", "")))
	_add_observation(str(recess_basketball_memory.get("later_behavior", "")))
	_add_observation(str(_get_dictionary(_selected_basketball_choice.get("relationship_effect", {})).get("behavior_feedback", "")))
	_add_relationship_debug_summary()
	_status_label = _add_observation("Recess keeps its own score somewhere off the page.")
	var rumor_button: Button = _make_button("Linger by the canteen shade")
	rumor_button.pressed.connect(_on_rumor_observed)
	_content.add_child(rumor_button)
	var save_button: Button = _make_button("Save the recess memory")
	save_button.pressed.connect(_on_save_pressed)
	_content.add_child(save_button)

func _on_rumor_observed() -> void:
	_selected_rumor = _get_first_rumor()
	if _selected_rumor.is_empty():
		_status_label.text = "The canteen shade keeps only the freezer hum."
		return
	discovered_rumor = {
		"id": str(_selected_rumor.get("id", "")),
		"source_id": str(_get_dictionary(_selected_rumor.get("source", {})).get("id", "")),
		"state": str(_selected_rumor.get("state", "")),
		"slice_end_status": str(_selected_rumor.get("slice_end_status", "unresolved"))
	}
	_show_rumor_observation()

func _show_rumor_observation() -> void:
	_clear_content()
	_set_school_light(Color(0.76, 0.78, 0.62))
	var source: Dictionary = _get_dictionary(_selected_rumor.get("source", {}))
	var discovery: Dictionary = _get_dictionary(_selected_rumor.get("discovery", {}))
	_add_heading("Canteen shade")
	_add_observation("%s, %s." % [str(discovery.get("time_anchor", "late recess")), str(discovery.get("place", "near the corridor"))])
	_add_observation(str(_selected_rumor.get("overheard_line", "")))
	_add_observation(str(_selected_rumor.get("source_behavior", "")))
	_add_observation(str(_selected_rumor.get("follow_up_observation", "")))
	_add_observation("%s's certainty feels like something you could learn, if you keep catching it beside the facts." % str(source.get("name", "Someone")))
	_add_rumor_debug_summary()
	_status_label = _add_observation("Nothing settles before the bell.")
	var save_button: Button = _make_button("Save the recess memory")
	save_button.pressed.connect(_on_save_pressed)
	_content.add_child(save_button)

func _on_save_pressed() -> void:
	var save_state: Dictionary = SaveService.new_save_state()
	var flags: Dictionary = {
		"class_seat": selected_seat_id,
		"shared_with": str(shared_experience.get("shared_with", "")),
		"independent_social_event": str(_independent_social_event.get("id", "")),
		"recess_basketball": selected_basketball_choice_id
	}
	var memory_log: Array = [
		{"id": "first_day_class_seat", "seat_id": selected_seat_id, "shared_with": str(shared_experience.get("shared_with", "")), "consequence": str(shared_experience.get("consequence", ""))},
		{"id": str(_independent_social_event.get("id", "")), "relationship": str(_independent_social_event.get("relationship", "")), "behavior": str(_independent_social_event.get("behavior_feedback", ""))},
		{"id": "recess_basketball", "choice_id": selected_basketball_choice_id, "outcome": str(recess_basketball_memory.get("outcome", "")), "later_behavior": str(recess_basketball_memory.get("later_behavior", ""))}
	]
	if not discovered_rumor.is_empty():
		flags["rumor"] = str(discovered_rumor.get("id", ""))
		flags["rumor_status"] = str(discovered_rumor.get("slice_end_status", "unresolved"))
		memory_log.append({"id": str(discovered_rumor.get("id", "")), "source_id": str(discovered_rumor.get("source_id", "")), "state": str(discovered_rumor.get("state", "")), "status": str(discovered_rumor.get("slice_end_status", "unresolved"))})
	save_state["current_scene"] = SCENE_PATH
	save_state["flags"] = flags
	save_state["memory_log"] = memory_log
	if OS.is_debug_build():
		save_state["debug_relationship_state"] = _relationship_state
		if not _selected_rumor.is_empty():
			save_state["debug_rumor"] = _selected_rumor
	if SaveService.save_game(save_state):
		_status_label.text = "The recess game settles into memory." if discovered_rumor.is_empty() else "The rumor stays unfinished in memory."
	else:
		_status_label.text = "The recess game slips before it can be saved."

func _apply_player_relationship_effect(effect: Dictionary) -> void:
	var target_id: String = str(effect.get("target", ""))
	if target_id.is_empty():
		return
	var player_relationships: Dictionary = _get_dictionary(_relationship_state.get("player", {}))
	var relationship: Dictionary = _get_dictionary(player_relationships.get(target_id, {}))
	relationship["familiarity"] = int(relationship.get("familiarity", 0)) + int(effect.get("familiarity_delta", 0))
	relationship["trust"] = int(relationship.get("trust", 0)) + int(effect.get("trust_delta", 0))
	relationship["tone"] = str(effect.get("tone", relationship.get("tone", "")))
	relationship["behavior"] = str(effect.get("behavior_feedback", relationship.get("behavior", "")))
	player_relationships[target_id] = relationship
	_relationship_state["player"] = player_relationships

func _apply_independent_social_event() -> void:
	var events: Array = _data.get("independent_social_events", [])
	if events.is_empty():
		_independent_social_event = {}
		return
	_independent_social_event = _get_dictionary(events[0])
	var relationship_id: String = str(_independent_social_event.get("relationship", ""))
	if relationship_id.is_empty():
		return
	var npc_relationships: Dictionary = _get_dictionary(_relationship_state.get("npc", {}))
	var relationship: Dictionary = _get_dictionary(npc_relationships.get(relationship_id, {}))
	relationship["tension"] = int(relationship.get("tension", 0)) + int(_independent_social_event.get("tension_delta", 0))
	relationship["tone"] = str(_independent_social_event.get("tone", relationship.get("tone", "")))
	relationship["behavior"] = str(_independent_social_event.get("behavior_feedback", relationship.get("behavior", "")))
	npc_relationships[relationship_id] = relationship
	_relationship_state["npc"] = npc_relationships

func _add_relationship_debug_summary() -> void:
	if not OS.is_debug_build():
		return
	var debug_label: Label = _add_observation("Debug relationship state: %s" % JSON.stringify(_relationship_state))
	debug_label.add_theme_font_size_override("font_size", 12)
	debug_label.add_theme_color_override("font_color", Color(0.28, 0.24, 0.18))

func _add_rumor_debug_summary() -> void:
	if not OS.is_debug_build():
		return
	var debug_label: Label = _add_observation("Debug rumor state: %s" % JSON.stringify(_selected_rumor))
	debug_label.add_theme_font_size_override("font_size", 12)
	debug_label.add_theme_color_override("font_color", Color(0.28, 0.24, 0.18))

func _get_first_rumor() -> Dictionary:
	var rumors: Array = _data.get("rumors", [])
	if rumors.is_empty():
		return {}
	return _get_dictionary(rumors[0])

func _get_dictionary(value: Variant) -> Dictionary:
	if value is Dictionary:
		return value.duplicate(true)
	return {}

func _set_school_light(color: Color) -> void:
	_background.color = color

func _add_heading(text: String) -> Label:
	var label: Label = Label.new()
	label.text = text
	label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	label.add_theme_font_size_override("font_size", 32)
	label.add_theme_color_override("font_color", Color(0.11, 0.12, 0.10))
	_content.add_child(label)
	return label

func _add_subheading(text: String) -> Label:
	var label: Label = Label.new()
	label.text = text
	label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	label.add_theme_font_size_override("font_size", 21)
	label.add_theme_color_override("font_color", Color(0.15, 0.15, 0.12))
	_content.add_child(label)
	return label

func _add_observation(text: String) -> Label:
	var label: Label = Label.new()
	label.text = text
	label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	label.add_theme_font_size_override("font_size", 17)
	label.add_theme_color_override("font_color", Color(0.16, 0.15, 0.12))
	label.custom_minimum_size = Vector2(780, 0)
	_content.add_child(label)
	return label

func _make_button(text: String) -> Button:
	var button: Button = Button.new()
	button.text = text
	button.custom_minimum_size = Vector2(340, 42)
	return button
