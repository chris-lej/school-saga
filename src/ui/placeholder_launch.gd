extends Control

const PLACEHOLDER_SCENE: String = "res://scenes/bootstrap/placeholder_launch.tscn"
const ProceduralAmbientSoundScript = preload("res://src/ui/procedural_ambient_sound.gd")

const ATMOSPHERE_ELEMENTS: PackedStringArray = [
	"person_washing_sidewalk",
	"dogs_audible_behind_gated_houses",
	"distant_traffic",
	"morning_birds",
	"neighbor_voices",
	"utility_poles",
	"overhead_wires",
	"painted_walls",
	"humid_vegetation",
	"uneven_sidewalks",
	"hopeful_morning_light",
]

var _status_label: Label
var _water_phase: float = 0.0

func _ready() -> void:
	_build_interface()
	_status_label.text = "Save schema v%s ready." % SaveService.CURRENT_SAVE_VERSION
	set_process(true)

func _process(delta: float) -> void:
	_water_phase = fmod(_water_phase + delta * 1.8, TAU)
	queue_redraw()

func _draw() -> void:
	var area: Rect2 = get_rect()
	var size: Vector2 = area.size
	_draw_sky(size)
	_draw_distant_houses(size)
	_draw_walls_and_gates(size)
	_draw_sidewalk(size)
	_draw_vegetation(size)
	_draw_utility_poles_and_wires(size)
	_draw_washing_neighbor(size)
	_draw_light(size)

func _build_interface() -> void:
	_build_ambient_audio()

	var margin: MarginContainer = MarginContainer.new()
	margin.set_anchors_preset(Control.PRESET_FULL_RECT)
	margin.add_theme_constant_override("margin_left", 34)
	margin.add_theme_constant_override("margin_top", 28)
	margin.add_theme_constant_override("margin_right", 34)
	margin.add_theme_constant_override("margin_bottom", 28)
	add_child(margin)

	var layout: VBoxContainer = VBoxContainer.new()
	layout.alignment = BoxContainer.ALIGNMENT_END
	layout.add_theme_constant_override("separation", 10)
	margin.add_child(layout)

	var title: Label = Label.new()
	title.text = "School Saga - Rua do Monte"
	title.horizontal_alignment = HORIZONTAL_ALIGNMENT_LEFT
	title.add_theme_font_size_override("font_size", 24)
	title.add_theme_color_override("font_color", Color(0.18, 0.13, 0.09))
	layout.add_child(title)

	var subtitle: Label = Label.new()
	subtitle.text = "A morning outside Colégio Monte Araucária."
	subtitle.horizontal_alignment = HORIZONTAL_ALIGNMENT_LEFT
	subtitle.add_theme_font_size_override("font_size", 15)
	subtitle.add_theme_color_override("font_color", Color(0.24, 0.18, 0.12))
	layout.add_child(subtitle)

	_status_label = Label.new()
	_status_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_LEFT
	_status_label.add_theme_color_override("font_color", Color(0.18, 0.13, 0.09))
	layout.add_child(_status_label)

	var actions: HBoxContainer = HBoxContainer.new()
	actions.alignment = BoxContainer.ALIGNMENT_CENTER
	actions.add_theme_constant_override("separation", 12)
	layout.add_child(actions)

	var save_button: Button = Button.new()
	save_button.text = "Save"
	save_button.pressed.connect(_on_save_pressed)
	actions.add_child(save_button)

	var load_button: Button = Button.new()
	load_button.text = "Load"
	load_button.pressed.connect(_on_load_pressed)
	actions.add_child(load_button)

	var reload_button: Button = Button.new()
	reload_button.text = "Reload"
	reload_button.pressed.connect(_on_reload_pressed)
	actions.add_child(reload_button)

func _build_ambient_audio() -> void:
	_add_ambient_sound("DogsBehindGates", "dogs behind gated houses", 92.0, 0.10, 2.4, 0.16, 0.35)
	_add_ambient_sound("DistantTraffic", "distant traffic", 58.0, 0.07, 4.2, 2.7, 0.22)
	_add_ambient_sound("MorningBirds", "morning birds", 1250.0, 0.055, 0.9, 0.08, 0.12)
	_add_ambient_sound("NeighborVoices", "neighbor voices", 180.0, 0.045, 3.6, 0.7, 0.18)

func _add_ambient_sound(
	node_name: String,
	label: String,
	base_hz: float,
	volume: float,
	pulse_interval: float,
	pulse_duration: float,
	texture_amount: float
) -> void:
	var sound := ProceduralAmbientSoundScript.new()
	sound.name = node_name
	sound.sound_label = label
	sound.base_hz = base_hz
	sound.volume = volume
	sound.pulse_interval = pulse_interval
	sound.pulse_duration = pulse_duration
	sound.texture_amount = texture_amount
	add_child(sound)

func _draw_sky(size: Vector2) -> void:
	draw_rect(Rect2(Vector2.ZERO, size), Color(0.76, 0.89, 0.95))
	draw_rect(Rect2(Vector2(0.0, size.y * 0.34), Vector2(size.x, size.y * 0.24)), Color(0.93, 0.82, 0.58, 0.62))
	draw_circle(Vector2(size.x * 0.13, size.y * 0.18), 72.0, Color(1.0, 0.82, 0.34, 0.55))

func _draw_distant_houses(size: Vector2) -> void:
	var base_y: float = size.y * 0.46
	var houses: Array[Dictionary] = [
		{"x": 0.02, "w": 0.18, "h": 0.18, "color": Color(0.87, 0.68, 0.47)},
		{"x": 0.21, "w": 0.16, "h": 0.22, "color": Color(0.72, 0.81, 0.68)},
		{"x": 0.55, "w": 0.20, "h": 0.20, "color": Color(0.91, 0.78, 0.63)},
		{"x": 0.76, "w": 0.18, "h": 0.24, "color": Color(0.66, 0.78, 0.82)},
	]
	for house in houses:
		var rect := Rect2(Vector2(size.x * float(house["x"]), base_y - size.y * float(house["h"])), Vector2(size.x * float(house["w"]), size.y * float(house["h"])))
		draw_rect(rect, house["color"])
		draw_colored_polygon(PackedVector2Array([
			Vector2(rect.position.x - 10.0, rect.position.y),
			Vector2(rect.position.x + rect.size.x * 0.5, rect.position.y - 42.0),
			Vector2(rect.position.x + rect.size.x + 10.0, rect.position.y),
		]), Color(0.55, 0.24, 0.18))

func _draw_walls_and_gates(size: Vector2) -> void:
	var wall_y: float = size.y * 0.49
	draw_rect(Rect2(Vector2(0.0, wall_y), Vector2(size.x, size.y * 0.18)), Color(0.82, 0.74, 0.61))
	for x in [size.x * 0.08, size.x * 0.34, size.x * 0.66, size.x * 0.86]:
		draw_rect(Rect2(Vector2(x, wall_y + 6.0), Vector2(82.0, size.y * 0.15)), Color(0.18, 0.24, 0.25))
		for bar_index in range(5):
			var bar_x: float = x + 10.0 + float(bar_index) * 15.0
			draw_line(Vector2(bar_x, wall_y + 8.0), Vector2(bar_x, wall_y + size.y * 0.15), Color(0.45, 0.52, 0.49), 3.0)
		draw_circle(Vector2(x + 24.0, wall_y + 72.0), 10.0, Color(0.20, 0.13, 0.08))
		draw_circle(Vector2(x + 44.0, wall_y + 69.0), 7.0, Color(0.20, 0.13, 0.08))
	for crack_x in [size.x * 0.18, size.x * 0.49, size.x * 0.73]:
		draw_line(Vector2(crack_x, wall_y + 8.0), Vector2(crack_x + 18.0, wall_y + 54.0), Color(0.48, 0.43, 0.36), 2.0)

func _draw_sidewalk(size: Vector2) -> void:
	var street_y: float = size.y * 0.67
	draw_rect(Rect2(Vector2(0.0, street_y), Vector2(size.x, size.y * 0.33)), Color(0.46, 0.45, 0.40))
	draw_rect(Rect2(Vector2(0.0, street_y), Vector2(size.x, 42.0)), Color(0.63, 0.60, 0.51))
	for index in range(12):
		var x: float = float(index) * size.x / 12.0
		var y_offset: float = sin(float(index) * 1.7) * 5.0
		draw_line(Vector2(x, street_y + y_offset), Vector2(x + size.x / 14.0, street_y + 42.0 - y_offset), Color(0.39, 0.38, 0.34), 2.0)
	for stone_index in range(8):
		var stone_x: float = size.x * 0.05 + float(stone_index) * size.x * 0.12
		draw_rect(Rect2(Vector2(stone_x, street_y + 52.0 + sin(stone_index) * 5.0), Vector2(58.0, 10.0)), Color(0.36, 0.35, 0.31))

func _draw_vegetation(size: Vector2) -> void:
	for x in [size.x * 0.04, size.x * 0.27, size.x * 0.51, size.x * 0.93]:
		draw_rect(Rect2(Vector2(x, size.y * 0.39), Vector2(14.0, size.y * 0.19)), Color(0.31, 0.23, 0.14))
		draw_circle(Vector2(x + 7.0, size.y * 0.36), 38.0, Color(0.22, 0.46, 0.25))
		draw_circle(Vector2(x + 32.0, size.y * 0.39), 27.0, Color(0.31, 0.56, 0.30))
	for plant_index in range(16):
		var x: float = float(plant_index) * size.x / 15.0
		draw_line(Vector2(x, size.y * 0.66), Vector2(x + 9.0, size.y * 0.60), Color(0.20, 0.43, 0.18), 3.0)

func _draw_utility_poles_and_wires(size: Vector2) -> void:
	var pole_color := Color(0.28, 0.20, 0.14)
	for x in [size.x * 0.17, size.x * 0.48, size.x * 0.79]:
		draw_rect(Rect2(Vector2(x, size.y * 0.18), Vector2(13.0, size.y * 0.49)), pole_color)
		draw_line(Vector2(x - 20.0, size.y * 0.25), Vector2(x + 34.0, size.y * 0.25), pole_color, 5.0)
	for wire_index in range(4):
		var y: float = size.y * (0.18 + float(wire_index) * 0.045)
		for segment in range(20):
			var start_x: float = float(segment) * size.x / 20.0
			var end_x: float = float(segment + 1) * size.x / 20.0
			var sag_a: float = sin(float(segment) * 0.9 + float(wire_index)) * 4.0
			var sag_b: float = sin(float(segment + 1) * 0.9 + float(wire_index)) * 4.0
			draw_line(Vector2(start_x, y + sag_a), Vector2(end_x, y + sag_b), Color(0.12, 0.15, 0.16), 2.0)

func _draw_washing_neighbor(size: Vector2) -> void:
	var origin := Vector2(size.x * 0.37, size.y * 0.63)
	draw_circle(origin + Vector2(0.0, -54.0), 12.0, Color(0.40, 0.24, 0.16))
	draw_line(origin + Vector2(0.0, -40.0), origin + Vector2(-6.0, -8.0), Color(0.26, 0.42, 0.74), 7.0)
	draw_line(origin + Vector2(-2.0, -30.0), origin + Vector2(38.0, -18.0), Color(0.58, 0.35, 0.18), 4.0)
	draw_line(origin + Vector2(-6.0, -8.0), origin + Vector2(-18.0, 18.0), Color(0.18, 0.22, 0.25), 5.0)
	draw_line(origin + Vector2(-3.0, -8.0), origin + Vector2(14.0, 18.0), Color(0.18, 0.22, 0.25), 5.0)
	var hose_start := origin + Vector2(38.0, -18.0)
	var water_end := origin + Vector2(120.0, 14.0 + sin(_water_phase) * 8.0)
	draw_line(hose_start, water_end, Color(0.18, 0.50, 0.73), 4.0)
	for stream_index in range(6):
		var offset: float = float(stream_index) * 8.0
		draw_line(
			hose_start + Vector2(offset * 0.22, offset * 0.08),
			water_end + Vector2(offset, sin(_water_phase + offset) * 6.0),
			Color(0.64, 0.86, 0.92, 0.55),
			2.0
		)
	draw_rect(Rect2(water_end + Vector2(-48.0, 8.0), Vector2(114.0, 24.0)), Color(0.58, 0.75, 0.77, 0.28))

func _draw_light(size: Vector2) -> void:
	draw_rect(Rect2(Vector2.ZERO, size), Color(1.0, 0.82, 0.42, 0.08))
	for glow_index in range(5):
		draw_circle(
			Vector2(size.x * 0.13, size.y * 0.18),
			96.0 + float(glow_index) * 62.0,
			Color(1.0, 0.78, 0.30, 0.05)
		)

func _on_save_pressed() -> void:
	var save_state: Dictionary = SaveService.new_save_state()
	save_state["current_scene"] = PLACEHOLDER_SCENE
	if SaveService.save_game(save_state):
		_status_label.text = "Saved schema v%s." % SaveService.CURRENT_SAVE_VERSION
	else:
		_status_label.text = "Save failed."

func _on_load_pressed() -> void:
	var save_state: Dictionary = SaveService.load_game()
	if save_state.is_empty():
		_status_label.text = "No compatible save found."
	else:
		_status_label.text = "Loaded schema v%s." % int(save_state["save_version"])

func _on_reload_pressed() -> void:
	if not SceneTransition.change_scene(PLACEHOLDER_SCENE):
		_status_label.text = "Scene reload failed."
