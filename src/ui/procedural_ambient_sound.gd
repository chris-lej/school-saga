extends AudioStreamPlayer

@export var sound_label: String = "ambient"
@export var base_hz: float = 220.0
@export var volume: float = 0.12
@export var pulse_interval: float = 1.0
@export var pulse_duration: float = 0.2
@export var texture_amount: float = 0.15

var _playback: AudioStreamGeneratorPlayback
var _phase: float = 0.0
var _time: float = 0.0
var _sample_rate: float = 16000.0

func _ready() -> void:
	var generated_stream: AudioStreamGenerator = AudioStreamGenerator.new()
	generated_stream.mix_rate = _sample_rate
	generated_stream.buffer_length = 0.35
	stream = generated_stream
	volume_db = linear_to_db(maxf(volume, 0.001))
	play()
	_playback = get_stream_playback() as AudioStreamGeneratorPlayback
	set_process(_playback != null)

func _process(_delta: float) -> void:
	if _playback == null:
		return

	var frames_available: int = _playback.get_frames_available()
	for _frame_index: int in range(frames_available):
		var sample: float = _sample()
		_playback.push_frame(Vector2(sample, sample))

func _sample() -> float:
	var pulse_position: float = fmod(_time, maxf(pulse_interval, 0.05))
	var envelope: float = 0.18
	if pulse_position <= pulse_duration:
		envelope = 1.0 - (pulse_position / maxf(pulse_duration, 0.01)) * 0.35

	var texture: float = sin((_phase * 0.37) + (sin(_time * 13.0) * 0.8)) * texture_amount
	var tone: float = sin(_phase) * envelope
	_phase = fmod(_phase + TAU * base_hz / _sample_rate, TAU)
	_time += 1.0 / _sample_rate
	return (tone + texture) * 0.18
