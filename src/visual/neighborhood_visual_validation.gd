extends Control

const PIXEL_VIEWPORT_SIZE: Vector2i = Vector2i(320, 180)
const CAMERA_CENTER: Vector2 = Vector2(160.0, 90.0)
const CAMERA_ZOOM: Vector2 = Vector2.ONE

class VisualCanvas:
	extends Node2D

	var water_phase: float = 0.0
	var dog_phase: float = 0.0
	var laundry_phase: float = 0.0

	func _ready() -> void:
		set_process(true)

	func _process(delta: float) -> void:
		water_phase = fmod(water_phase + delta * 2.5, TAU)
		dog_phase = fmod(dog_phase + delta * 5.0, TAU)
		laundry_phase = fmod(laundry_phase + delta * 1.6, TAU)
		queue_redraw()

	func _draw() -> void:
		_draw_sky_and_mood()
		_draw_practical_architecture()
		_draw_school_gate()
		_draw_uneven_surfaces()
		_draw_faded_materials()
		_draw_vegetation()
		_draw_wires()
		_draw_expressive_ambient_motion()
		_draw_painterly_light()

	func _draw_sky_and_mood() -> void:
		draw_rect(Rect2(Vector2.ZERO, Vector2(320.0, 180.0)), Color(0.49, 0.68, 0.78))
		draw_rect(Rect2(Vector2(0.0, 0.0), Vector2(320.0, 62.0)), Color(0.84, 0.73, 0.52, 0.58))
		draw_rect(Rect2(Vector2(0.0, 50.0), Vector2(320.0, 54.0)), Color(0.93, 0.69, 0.35, 0.20))
		draw_circle(Vector2(47.0, 26.0), 19.0, Color(1.0, 0.82, 0.34, 0.72))

	func _draw_practical_architecture() -> void:
		draw_rect(Rect2(Vector2(0.0, 71.0), Vector2(320.0, 54.0)), Color(0.66, 0.57, 0.45))
		draw_rect(Rect2(Vector2(0.0, 73.0), Vector2(92.0, 48.0)), Color(0.71, 0.62, 0.49))
		draw_rect(Rect2(Vector2(97.0, 66.0), Vector2(88.0, 58.0)), Color(0.78, 0.72, 0.58))
		draw_rect(Rect2(Vector2(219.0, 61.0), Vector2(101.0, 62.0)), Color(0.62, 0.72, 0.70))
		draw_colored_polygon(PackedVector2Array([Vector2(97.0, 66.0), Vector2(141.0, 42.0), Vector2(185.0, 66.0)]), Color(0.42, 0.21, 0.17))
		draw_colored_polygon(PackedVector2Array([Vector2(217.0, 61.0), Vector2(270.0, 38.0), Vector2(322.0, 61.0)]), Color(0.36, 0.25, 0.20))
		for tile_x in range(104, 178, 9):
			draw_line(Vector2(float(tile_x), 62.0), Vector2(float(tile_x + 8), 58.0), Color(0.52, 0.25, 0.18), 1.0)
		draw_rect(Rect2(Vector2(111.0, 84.0), Vector2(28.0, 25.0)), Color(0.22, 0.28, 0.30))
		draw_rect(Rect2(Vector2(149.0, 88.0), Vector2(25.0, 19.0)), Color(0.32, 0.43, 0.48))
		draw_rect(Rect2(Vector2(231.0, 82.0), Vector2(30.0, 28.0)), Color(0.18, 0.25, 0.24))
		draw_rect(Rect2(Vector2(271.0, 78.0), Vector2(34.0, 31.0)), Color(0.25, 0.33, 0.34))

	func _draw_school_gate() -> void:
		draw_rect(Rect2(Vector2(5.0, 83.0), Vector2(74.0, 43.0)), Color(0.16, 0.23, 0.24))
		for bar_x in range(10, 77, 8):
			draw_line(Vector2(float(bar_x), 84.0), Vector2(float(bar_x), 126.0), Color(0.41, 0.49, 0.45), 2.0)
		draw_line(Vector2(7.0, 98.0), Vector2(77.0, 98.0), Color(0.48, 0.55, 0.49), 2.0)
		draw_line(Vector2(7.0, 116.0), Vector2(77.0, 116.0), Color(0.33, 0.39, 0.36), 2.0)
		draw_rect(Rect2(Vector2(13.0, 78.0), Vector2(50.0, 8.0)), Color(0.75, 0.69, 0.52))
		draw_rect(Rect2(Vector2(16.0, 80.0), Vector2(44.0, 3.0)), Color(0.52, 0.47, 0.35))

	func _draw_uneven_surfaces() -> void:
		draw_rect(Rect2(Vector2(0.0, 125.0), Vector2(320.0, 55.0)), Color(0.42, 0.41, 0.36))
		draw_colored_polygon(PackedVector2Array([
			Vector2(0.0, 123.0), Vector2(54.0, 127.0), Vector2(118.0, 124.0),
			Vector2(183.0, 130.0), Vector2(252.0, 125.0), Vector2(320.0, 128.0),
			Vector2(320.0, 149.0), Vector2(0.0, 148.0)
		]), Color(0.63, 0.59, 0.50))
		for paver_x in range(0, 320, 25):
			var lift: float = sin(float(paver_x) * 0.11) * 2.0
			draw_line(Vector2(float(paver_x), 126.0 + lift), Vector2(float(paver_x + 17), 148.0 - lift), Color(0.35, 0.34, 0.30), 1.0)
		for crack_x in [28.0, 83.0, 157.0, 214.0, 291.0]:
			draw_line(Vector2(crack_x, 131.0), Vector2(crack_x + 8.0, 145.0), Color(0.22, 0.23, 0.22), 1.0)
			draw_line(Vector2(crack_x + 8.0, 145.0), Vector2(crack_x + 3.0, 151.0), Color(0.22, 0.23, 0.22), 1.0)
		for stone_x in range(15, 311, 38):
			draw_rect(Rect2(Vector2(float(stone_x), 159.0 + sin(float(stone_x)) * 2.0), Vector2(25.0, 5.0)), Color(0.31, 0.31, 0.28))

	func _draw_faded_materials() -> void:
		for stain in [
			Rect2(Vector2(103.0, 76.0), Vector2(24.0, 5.0)),
			Rect2(Vector2(130.0, 111.0), Vector2(41.0, 4.0)),
			Rect2(Vector2(225.0, 68.0), Vector2(62.0, 5.0)),
			Rect2(Vector2(4.0, 112.0), Vector2(62.0, 5.0)),
		]:
			draw_rect(stain, Color(0.44, 0.40, 0.33, 0.44))
		for chip in [Vector2(96.0, 91.0), Vector2(181.0, 75.0), Vector2(245.0, 113.0), Vector2(300.0, 96.0)]:
			draw_rect(Rect2(chip, Vector2(5.0, 3.0)), Color(0.91, 0.85, 0.70, 0.70))

	func _draw_vegetation() -> void:
		for tree_x in [91.0, 207.0, 300.0]:
			draw_rect(Rect2(Vector2(tree_x, 58.0), Vector2(7.0, 67.0)), Color(0.31, 0.20, 0.13))
			draw_circle(Vector2(tree_x + 3.0, 50.0), 19.0, Color(0.18, 0.42, 0.22))
			draw_circle(Vector2(tree_x - 10.0, 63.0), 15.0, Color(0.25, 0.52, 0.27))
			draw_circle(Vector2(tree_x + 16.0, 62.0), 17.0, Color(0.30, 0.55, 0.26))
		for grass_x in range(3, 320, 7):
			var height: float = 4.0 + fmod(float(grass_x), 5.0)
			draw_line(Vector2(float(grass_x), 126.0), Vector2(float(grass_x + 2), 126.0 - height), Color(0.18, 0.43, 0.18), 1.0)

	func _draw_wires() -> void:
		for pole_x in [42.0, 190.0, 280.0]:
			draw_rect(Rect2(Vector2(pole_x, 31.0), Vector2(5.0, 97.0)), Color(0.24, 0.17, 0.12))
			draw_line(Vector2(pole_x - 9.0, 45.0), Vector2(pole_x + 15.0, 45.0), Color(0.24, 0.17, 0.12), 2.0)
		for wire_index in range(5):
			var y: float = 27.0 + float(wire_index) * 7.0
			var points := PackedVector2Array()
			for segment in range(17):
				var x: float = float(segment) * 20.0
				points.append(Vector2(x, y + sin(float(segment) * 0.8 + float(wire_index)) * 2.0))
			draw_polyline(points, Color(0.09, 0.12, 0.13), 1.0)

	func _draw_expressive_ambient_motion() -> void:
		var tail_y: float = 105.0 + sin(dog_phase) * 2.0
		draw_circle(Vector2(31.0, 111.0), 6.0, Color(0.16, 0.10, 0.07))
		draw_line(Vector2(25.0, 110.0), Vector2(19.0, tail_y), Color(0.16, 0.10, 0.07), 2.0)

		var cloth_lift: float = sin(laundry_phase) * 2.0
		draw_line(Vector2(222.0, 64.0), Vector2(296.0, 58.0), Color(0.13, 0.16, 0.16), 1.0)
		draw_rect(Rect2(Vector2(238.0, 64.0 + cloth_lift), Vector2(12.0, 13.0)), Color(0.85, 0.47, 0.34))
		draw_rect(Rect2(Vector2(260.0, 62.0 - cloth_lift), Vector2(15.0, 12.0)), Color(0.88, 0.82, 0.65))

		var washer := Vector2(137.0, 121.0)
		draw_circle(washer + Vector2(0.0, -22.0), 4.0, Color(0.37, 0.21, 0.14))
		draw_line(washer + Vector2(0.0, -17.0), washer + Vector2(-2.0, -4.0), Color(0.27, 0.45, 0.70), 3.0)
		draw_line(washer + Vector2(0.0, -13.0), washer + Vector2(17.0, -9.0), Color(0.50, 0.31, 0.17), 2.0)
		draw_line(washer + Vector2(-2.0, -4.0), washer + Vector2(-7.0, 6.0), Color(0.17, 0.20, 0.22), 2.0)
		draw_line(washer + Vector2(-1.0, -4.0), washer + Vector2(7.0, 6.0), Color(0.17, 0.20, 0.22), 2.0)
		var water_end := washer + Vector2(54.0, 6.0 + sin(water_phase) * 3.0)
		draw_line(washer + Vector2(17.0, -9.0), water_end, Color(0.40, 0.69, 0.82), 2.0)
		draw_rect(Rect2(water_end + Vector2(-17.0, 3.0), Vector2(44.0, 7.0)), Color(0.54, 0.76, 0.78, 0.32))

	func _draw_painterly_light() -> void:
		for glow in range(6):
			draw_circle(Vector2(47.0, 26.0), 32.0 + float(glow) * 24.0, Color(1.0, 0.72, 0.25, 0.045))
		draw_colored_polygon(PackedVector2Array([
			Vector2(39.0, 39.0), Vector2(86.0, 125.0), Vector2(174.0, 125.0), Vector2(63.0, 35.0)
		]), Color(1.0, 0.76, 0.34, 0.18))
		draw_rect(Rect2(Vector2(0.0, 126.0), Vector2(320.0, 54.0)), Color(0.19, 0.20, 0.20, 0.18))
		draw_rect(Rect2(Vector2.ZERO, Vector2(320.0, 180.0)), Color(0.88, 0.58, 0.26, 0.06))

var _viewport_container: SubViewportContainer
var _viewport: SubViewport
var _camera: Camera2D

func _ready() -> void:
	_build_pixel_viewport()

func _notification(what: int) -> void:
	if what == NOTIFICATION_RESIZED and _viewport_container != null:
		_fit_pixel_viewport()

func _build_pixel_viewport() -> void:
	_viewport_container = SubViewportContainer.new()
	_viewport_container.name = "FixedPixelViewportContainer"
	_viewport_container.stretch = true
	_viewport_container.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	_viewport_container.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(_viewport_container)

	_viewport = SubViewport.new()
	_viewport.name = "PixelViewport"
	_viewport.size = PIXEL_VIEWPORT_SIZE
	_viewport.disable_3d = true
	_viewport.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	_viewport.canvas_item_default_texture_filter = Viewport.DEFAULT_CANVAS_ITEM_TEXTURE_FILTER_NEAREST
	_viewport_container.add_child(_viewport)

	var canvas := VisualCanvas.new()
	canvas.name = "RuaDoMonteVisualCanvas"
	_viewport.add_child(canvas)

	_camera = Camera2D.new()
	_camera.name = "FixedPixelCamera"
	_camera.position = CAMERA_CENTER.round()
	_camera.zoom = CAMERA_ZOOM
	_camera.position_smoothing_enabled = false
	_camera.rotation_smoothing_enabled = false
	_camera.enabled = true
	_camera.make_current()
	_viewport.add_child(_camera)
	_fit_pixel_viewport()

func _fit_pixel_viewport() -> void:
	var available_size: Vector2 = get_rect().size
	var scale_x: int = maxi(1, int(floor(available_size.x / float(PIXEL_VIEWPORT_SIZE.x))))
	var scale_y: int = maxi(1, int(floor(available_size.y / float(PIXEL_VIEWPORT_SIZE.y))))
	var integer_scale: int = mini(scale_x, scale_y)
	var base_size := Vector2(float(PIXEL_VIEWPORT_SIZE.x), float(PIXEL_VIEWPORT_SIZE.y))
	var display_size := base_size * float(integer_scale)
	_viewport_container.size = display_size
	_viewport_container.position = ((available_size - display_size) * 0.5).round()
