extends Control

const MORNING_DATA_PATH: String = "res://data/opening_morning.json"
const SCHOOL_FIRST_DAY_SCENE_PATH: String = "res://scenes/locations/school_first_day.tscn"
const DEFAULT_PROTAGONIST_NAME: String = "Novo estudante"

var protagonist_name: String = DEFAULT_PROTAGONIST_NAME
var breakfast_choice_id: String = ""
var morning_flags: Dictionary = {}

var _data: Dictionary = {}
var _background: ColorRect
var _panel: MarginContainer
var _content: VBoxContainer
var _name_input: LineEdit
var _status_label: Label

func _ready() -> void:
	_data = _load_morning_data()
	_build_shell()
	_show_character_entry()

func _load_morning_data() -> Dictionary:
	var file: FileAccess = FileAccess.open(MORNING_DATA_PATH, FileAccess.READ)
	if file == null:
		push_warning("Opening morning data could not be loaded.")
		return {
			"bedroom_observations": [],
			"threshold_observations": [],
			"breakfast_choices": []
		}

	var parsed: Variant = JSON.parse_string(file.get_as_text())
	if parsed is Dictionary:
		return parsed

	push_warning("Opening morning data is not a JSON object.")
	return {
		"bedroom_observations": [],
		"threshold_observations": [],
		"breakfast_choices": []
	}

func _build_shell() -> void:
	_background = ColorRect.new()
	_background.color = Color(0.94, 0.78, 0.52)
	_background.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(_background)

	_panel = MarginContainer.new()
	_panel.set_anchors_preset(Control.PRESET_FULL_RECT)
	_panel.add_theme_constant_override("margin_left", 64)
	_panel.add_theme_constant_override("margin_top", 56)
	_panel.add_theme_constant_override("margin_right", 64)
	_panel.add_theme_constant_override("margin_bottom", 56)
	add_child(_panel)

	_content = VBoxContainer.new()
	_content.alignment = BoxContainer.ALIGNMENT_CENTER
	_content.add_theme_constant_override("separation", 16)
	_panel.add_child(_content)

func _clear_content() -> void:
	for child: Node in _content.get_children():
		child.queue_free()

func _show_character_entry() -> void:
	_clear_content()
	_set_morning_light(Color(0.95, 0.79, 0.55))

	_add_heading("Primeira manha")
	_add_observation("The room is still half-blue, half-gold. Somewhere beyond the window, Curitiba has already started without waiting.")
	_add_observation("A school uniform hangs from the chair. The name on the notebook is still the easiest part to change.")

	_name_input = LineEdit.new()
	_name_input.placeholder_text = DEFAULT_PROTAGONIST_NAME
	_name_input.text = protagonist_name
	_name_input.alignment = HORIZONTAL_ALIGNMENT_CENTER
	_name_input.custom_minimum_size = Vector2(360, 44)
	_content.add_child(_name_input)

	var continue_button: Button = _make_button("Open the window")
	continue_button.pressed.connect(_on_character_entry_confirmed)
	_content.add_child(continue_button)

func _on_character_entry_confirmed() -> void:
	var typed_name: String = _name_input.text.strip_edges()
	if typed_name.is_empty():
		protagonist_name = DEFAULT_PROTAGONIST_NAME
	else:
		protagonist_name = typed_name

	morning_flags["protagonist_named"] = protagonist_name != DEFAULT_PROTAGONIST_NAME
	_show_bedroom()

func _show_bedroom() -> void:
	_clear_content()
	_set_morning_light(Color(0.98, 0.82, 0.58))

	_add_heading("Bedroom")
	_add_observation("%s stands in the soft morning light, close enough to childhood that the room still knows every old habit." % protagonist_name)
	for observation: String in _data.get("bedroom_observations", []):
		_add_observation(observation)

	var continue_button: Button = _make_button("Go to the kitchen")
	continue_button.pressed.connect(_show_breakfast)
	_content.add_child(continue_button)

func _show_breakfast() -> void:
	_clear_content()
	_set_morning_light(Color(0.91, 0.74, 0.48))

	_add_heading("Kitchen")
	_add_observation("The table has a vinyl cloth, a chipped mug, and the quiet pressure of a school morning.")
	_add_observation("Breakfast is small enough to seem harmless. The day makes room for it anyway.")

	var choices: Array = _data.get("breakfast_choices", [])
	for choice: Dictionary in choices:
		var choice_button: Button = _make_button(str(choice.get("label", "")))
		choice_button.pressed.connect(_on_breakfast_selected.bind(choice))
		_content.add_child(choice_button)

func _on_breakfast_selected(choice: Dictionary) -> void:
	breakfast_choice_id = str(choice.get("id", ""))
	morning_flags["breakfast_choice"] = breakfast_choice_id
	_show_threshold(str(choice.get("kitchen_observation", "")), str(choice.get("threshold_consequence", "")))

func _show_threshold(kitchen_observation: String, threshold_consequence: String) -> void:
	_clear_content()
	_set_morning_light(Color(0.74, 0.84, 0.82))

	_add_heading("Neighborhood threshold")
	if not kitchen_observation.is_empty():
		_add_observation(kitchen_observation)
	for observation: String in _data.get("threshold_observations", []):
		_add_observation(observation)
	if not threshold_consequence.is_empty():
		_add_observation(threshold_consequence)

	_status_label = _add_observation("Home is behind you. The neighborhood is awake ahead.")

	var save_button: Button = _make_button("Save this morning")
	save_button.pressed.connect(_on_save_pressed)
	_content.add_child(save_button)

	var school_button: Button = _make_button("Go to Colegio Monte Araucaria")
	school_button.pressed.connect(_on_go_to_school_pressed)
	_content.add_child(school_button)

func _on_save_pressed() -> void:
	var save_state: Dictionary = SaveService.new_save_state()
	save_state["current_scene"] = "res://scenes/locations/home_morning.tscn"
	save_state["flags"] = morning_flags.duplicate(true)
	save_state["memory_log"] = [
		{
			"id": "opening_morning",
			"protagonist_name": protagonist_name,
			"breakfast_choice": breakfast_choice_id
		}
	]

	if SaveService.save_game(save_state):
		_status_label.text = "The morning settles into memory."
	else:
		_status_label.text = "The morning slips before it can be saved."

func _on_go_to_school_pressed() -> void:
	if not SceneTransition.change_scene(SCHOOL_FIRST_DAY_SCENE_PATH):
		_status_label.text = "The school morning stays just out of reach."

func _set_morning_light(color: Color) -> void:
	_background.color = color

func _add_heading(text: String) -> Label:
	var label: Label = Label.new()
	label.text = text
	label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	label.add_theme_font_size_override("font_size", 34)
	label.add_theme_color_override("font_color", Color(0.15, 0.12, 0.10))
	_content.add_child(label)
	return label

func _add_observation(text: String) -> Label:
	var label: Label = Label.new()
	label.text = text
	label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	label.add_theme_font_size_override("font_size", 18)
	label.add_theme_color_override("font_color", Color(0.18, 0.15, 0.12))
	label.custom_minimum_size = Vector2(720, 0)
	_content.add_child(label)
	return label

func _make_button(text: String) -> Button:
	var button: Button = Button.new()
	button.text = text
	button.custom_minimum_size = Vector2(280, 44)
	return button
