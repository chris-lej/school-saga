extends Control

const SCHOOL_SCENE: String = "res://scenes/locations/school_first_day.tscn"
const ProceduralAmbientSoundScript = preload("res://src/ui/procedural_ambient_sound.gd")

var _status_label: Label
var _water_phase: float = 0.0

func _ready() -> void:
	_build_interface()
	set_process(true)

func _process(delta: float) -> void:
	_water_phase = fmod(_water_phase + delta * 1.8, TAU)
	queue_redraw()

func _draw() -> void:
	var size: Vector2 = get_rect().size
	draw_rect(Rect2(Vector2.ZERO, size), Color(0.76, 0.89, 0.95))
	draw_rect(Rect2(Vector2(0.0, size.y * 0.34), Vector2(size.x, size.y * 0.24)), Color(0.93, 0.82, 0.58, 0.62))
	draw_circle(Vector2(size.x * 0.13, size.y * 0.18), 72.0, Color(1.0, 0.82, 0.34, 0.55))

	var street_y: float = size.y * 0.67
	draw_rect(Rect2(Vector2(0.0, street_y), Vector2(size.x, size.y * 0.33)), Color(0.46, 0.45, 0.40))
	draw_rect(Rect2(Vector2(0.0, street_y), Vector2(size.x, 42.0)), Color(0.63, 0.60, 0.51))

	for x in [size.x * 0.17, size.x * 0.48, size.x * 0.79]:
		draw_rect(Rect2(Vector2(x, size.y * 0.18), Vector2(13.0, size.y * 0.49)), Color(0.28, 0.20, 0.14))
		draw_line(Vector2(x - 20.0, size.y * 0.25), Vector2(x + 34.0, size.y * 0.25), Color(0.28, 0.20, 0.14), 5.0)

	for wire_index in range(4):
		var y: float = size.y * (0.18 + float(wire_index) * 0.045)
		for segment in range(20):
			var start_x: float = float(segment) * size.x / 20.0
			var end_x: float = float(segment + 1) * size.x / 20.0
			draw_line(Vector2(start_x, y + sin(float(segment) * 0.9) * 4.0), Vector2(end_x, y + sin(float(segment + 1) * 0.9) * 4.0), Color(0.12, 0.15, 0.16), 2.0)

	var origin := Vector2(size.x * 0.37, size.y * 0.63)
	draw_circle(origin + Vector2(0.0, -54.0), 12.0, Color(0.40, 0.24, 0.16))
	draw_line(origin + Vector2(0.0, -40.0), origin + Vector2(-6.0, -8.0), Color(0.26, 0.42, 0.74), 7.0)
	var hose_start := origin + Vector2(38.0, -18.0)
	var water_end := origin + Vector2(120.0, 14.0 + sin(_water_phase) * 8.0)
	draw_line(hose_start, water_end, Color(0.64, 0.86, 0.92, 0.55), 2.0)
	draw_rect(Rect2(Vector2.ZERO, size), Color(1.0, 0.82, 0.42, 0.08))

func _build_interface() -> void:
	_add_ambient_sound("DogsBehindGates", "dogs behind gated houses", 92.0, 0.10, 2.4, 0.16, 0.35)
	_add_ambient_sound("DistantTraffic", "distant traffic", 58.0, 0.07, 4.2, 2.7, 0.22)
	_add_ambient_sound("MorningBirds", "morning birds", 1250.0, 0.055, 0.9, 0.08, 0.12)

	var margin := MarginContainer.new()
	margin.set_anchors_preset(Control.PRESET_FULL_RECT)
	margin.add_theme_constant_override("margin_left", 34)
	margin.add_theme_constant_override("margin_top", 28)
	margin.add_theme_constant_override("margin_right", 34)
	margin.add_theme_constant_override("margin_bottom", 28)
	add_child(margin)

	var layout := VBoxContainer.new()
	layout.alignment = BoxContainer.ALIGNMENT_END
	layout.add_theme_constant_override("separation", 10)
	margin.add_child(layout)

	var title := Label.new()
	title.text = "Rua do Monte"
	title.add_theme_font_size_override("font_size", 24)
	layout.add_child(title)

	var subtitle := Label.new()
	subtitle.text = "The school gate is a short walk ahead."
	layout.add_child(subtitle)

	_status_label = Label.new()
	_status_label.text = "Continue when you are ready to enter Colégio Monte Araucária."
	layout.add_child(_status_label)

	var continue_button := Button.new()
	continue_button.text = "Continue to school"
	continue_button.pressed.connect(_on_continue_pressed)
	layout.add_child(continue_button)

func _add_ambient_sound(node_name: String, label: String, base_hz: float, volume: float, pulse_interval: float, pulse_duration: float, texture_amount: float) -> void:
	var sound := ProceduralAmbientSoundScript.new()
	sound.name = node_name
	sound.sound_label = label
	sound.base_hz = base_hz
	sound.volume = volume
	sound.pulse_interval = pulse_interval
	sound.pulse_duration = pulse_duration
	sound.texture_amount = texture_amount
	add_child(sound)

func _on_continue_pressed() -> void:
	if not SceneTransition.change_scene(SCHOOL_SCENE):
		_status_label.text = "Could not enter the school scene."
