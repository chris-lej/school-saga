extends Control

const SCENE_PATH: String = "res://scenes/locations/return_home.tscn"
const HOME_MORNING_SCENE_PATH: String = "res://scenes/locations/home_morning.tscn"

var _background: ColorRect
var _content: VBoxContainer
var _status_label: Label
var _saved_state: Dictionary = {}

func _ready() -> void:
	_saved_state = SaveService.load_game()
	_build_shell()
	_show_evening_summary()

func _build_shell() -> void:
	_background = ColorRect.new()
	_background.color = Color(0.32, 0.35, 0.46)
	_background.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(_background)

	var panel := MarginContainer.new()
	panel.set_anchors_preset(Control.PRESET_FULL_RECT)
	panel.add_theme_constant_override("margin_left", 64)
	panel.add_theme_constant_override("margin_top", 48)
	panel.add_theme_constant_override("margin_right", 64)
	panel.add_theme_constant_override("margin_bottom", 48)
	add_child(panel)

	_content = VBoxContainer.new()
	_content.alignment = BoxContainer.ALIGNMENT_CENTER
	_content.add_theme_constant_override("separation", 14)
	panel.add_child(_content)

func _show_evening_summary() -> void:
	_add_heading("Back home")
	_add_observation("The gate clicks shut again, softer than it did this morning. The neighborhood keeps moving without asking what happened at school.")

	var flags: Dictionary = _saved_state.get("flags", {})
	if str(flags.get("class_seat", "")).is_empty():
		_add_observation("The day returns as fragments: chalk dust, voices in the courtyard, and the feeling that tomorrow already has unfinished edges.")
	else:
		_add_observation("The seat you chose still seems to hold a shape in your memory.")

	if not str(flags.get("recess_basketball", "")).is_empty():
		_add_observation("Somewhere behind the school wall, the recess game probably kept going after you stopped watching it.")

	if not str(flags.get("rumor", "")).is_empty():
		_add_observation("The storage-room rumor follows you home without becoming any more certain.")

	_status_label = _add_observation("The first day settles, but not completely.")

	var save_button := _make_button("Save the completed first day")
	save_button.pressed.connect(_on_save_pressed)
	_content.add_child(save_button)

	var restart_button := _make_button("Begin another morning")
	restart_button.pressed.connect(_on_restart_pressed)
	_content.add_child(restart_button)

func _on_save_pressed() -> void:
	var save_state: Dictionary = _saved_state.duplicate(true)
	if save_state.is_empty():
		save_state = SaveService.new_save_state()
	var flags: Dictionary = save_state.get("flags", {}).duplicate(true)
	flags["first_day_complete"] = true
	save_state["flags"] = flags
	save_state["current_scene"] = SCENE_PATH
	var memory_log: Array = save_state.get("memory_log", []).duplicate(true)
	memory_log.append({
		"id": "first_day_return_home",
		"status": "complete"
	})
	save_state["memory_log"] = memory_log
	if SaveService.save_game(save_state):
		_saved_state = save_state
		_status_label.text = "The whole first day settles into memory."
	else:
		_status_label.text = "The evening slips before it can be saved."

func _on_restart_pressed() -> void:
	if not SceneTransition.change_scene(HOME_MORNING_SCENE_PATH):
		_status_label.text = "Tomorrow stays just out of reach."

func _add_heading(text: String) -> Label:
	var label := Label.new()
	label.text = text
	label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	label.add_theme_font_size_override("font_size", 34)
	label.add_theme_color_override("font_color", Color(0.92, 0.88, 0.76))
	_content.add_child(label)
	return label

func _add_observation(text: String) -> Label:
	var label := Label.new()
	label.text = text
	label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	label.add_theme_font_size_override("font_size", 18)
	label.add_theme_color_override("font_color", Color(0.88, 0.85, 0.78))
	label.custom_minimum_size = Vector2(760, 0)
	_content.add_child(label)
	return label

func _make_button(text: String) -> Button:
	var button := Button.new()
	button.text = text
	button.custom_minimum_size = Vector2(340, 44)
	return button
