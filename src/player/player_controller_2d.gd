extends CharacterBody2D
class_name PlayerController2D

@export_range(1.0, 600.0, 1.0, "or_greater") var movement_speed: float = 140.0
@export var input_enabled: bool = true
@export var move_left_action: StringName = &"player_move_left"
@export var move_right_action: StringName = &"player_move_right"
@export var move_up_action: StringName = &"player_move_up"
@export var move_down_action: StringName = &"player_move_down"
@export var interact_action: StringName = &"player_interact"
@export var cancel_action: StringName = &"player_cancel"
@export var run_action: StringName = &"player_run"

var facing_direction: Vector2 = Vector2.DOWN
var facing_animation_direction: StringName = &"down"
var is_moving: bool = false
var movement_direction: Vector2 = Vector2.ZERO

@onready var animated_sprite: AnimatedSprite2D = %PlayerAnimatedSprite
@onready var interaction_anchor: Marker2D = %InteractionAnchor
@onready var facing_direction_marker: Marker2D = %FacingDirectionMarker

func _ready() -> void:
	_update_direction_markers()
	_update_animation_state()

func _physics_process(_delta: float) -> void:
	var input_direction: Vector2 = Vector2.ZERO
	if input_enabled:
		input_direction = Input.get_vector(
			move_left_action,
			move_right_action,
			move_up_action,
			move_down_action
		)

	apply_movement_input(input_direction)
	move_and_slide()

func apply_movement_input(input_direction: Vector2) -> void:
	movement_direction = get_normalized_movement_direction(input_direction)
	velocity = movement_direction * movement_speed
	is_moving = not movement_direction.is_zero_approx()

	if is_moving:
		facing_direction = movement_direction
		facing_animation_direction = _get_cardinal_direction_name(movement_direction)
		_update_direction_markers()
	_update_animation_state()

func get_normalized_movement_direction(input_direction: Vector2) -> Vector2:
	if input_direction.is_zero_approx():
		return Vector2.ZERO

	return input_direction.normalized()

func get_facing_direction() -> Vector2:
	return facing_direction

func get_facing_animation_direction() -> StringName:
	return facing_animation_direction

func get_current_animation_name() -> StringName:
	if is_moving:
		return StringName("walk_%s" % facing_animation_direction)

	return StringName("idle_%s" % facing_animation_direction)

func get_interaction_anchor_global_position() -> Vector2:
	return interaction_anchor.global_position

func is_interact_just_pressed() -> bool:
	return input_enabled and Input.is_action_just_pressed(interact_action)

func is_cancel_just_pressed() -> bool:
	return input_enabled and Input.is_action_just_pressed(cancel_action)

func is_run_pressed() -> bool:
	return input_enabled and Input.is_action_pressed(run_action)

func _update_direction_markers() -> void:
	var marker_offset: Vector2 = facing_direction * 18.0
	interaction_anchor.position = marker_offset
	facing_direction_marker.position = marker_offset

func _update_animation_state() -> void:
	var animation_name: StringName = get_current_animation_name()
	if animated_sprite.animation != animation_name:
		animated_sprite.play(animation_name)
	elif not animated_sprite.is_playing():
		animated_sprite.play()

func _get_cardinal_direction_name(direction: Vector2) -> StringName:
	if absf(direction.x) > absf(direction.y):
		if direction.x < 0.0:
			return &"left"
		return &"right"

	if direction.y < 0.0:
		return &"up"
	return &"down"
