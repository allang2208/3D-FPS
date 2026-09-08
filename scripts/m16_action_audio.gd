extends Node
## Times are source-animation seconds, advanced by the same clock as the pose.
signal cue_played(cue: StringName, clip_time: float)

const STREAMS := {
	&"mag_out": preload("res://assets/sfx/m16/mechanics/mag_out.wav"),
	&"mag_insert": preload("res://assets/sfx/m16/mechanics/mag_insert.wav"),
	&"mag_seat": preload("res://assets/sfx/m16/mechanics/mag_seat.wav"),
	&"charge_pull": preload("res://assets/sfx/m16/mechanics/charge_pull.wav"),
	&"charge_release": preload("res://assets/sfx/m16/mechanics/charge_release.wav"),
	&"bolt_release": preload("res://assets/sfx/m16/mechanics/bolt_release.wav"),
}
const CUES := {
	&"reload": [[0.733333, &"mag_out"], [1.4, &"mag_insert"], [1.533333, &"mag_seat"], [1.833333, &"bolt_release"]],
	&"reload_empty": [[0.6, &"mag_out"], [1.266667, &"mag_insert"], [1.4, &"mag_seat"], [1.633333, &"charge_pull"], [1.966667, &"charge_release"]],
	&"equip_charge": [[0.453333, &"charge_pull"], [0.786667, &"charge_release"]],
}
var _players := {}
var _cues: Array = []
var _next := 0
var _time := 0.0
var _speed := 1.0

func _ready() -> void:
	for cue: StringName in STREAMS:
		var voice := AudioStreamPlayer.new()
		voice.name = cue
		voice.stream = STREAMS[cue]
		voice.bus = "SFX"
		voice.volume_db = -4.0
		add_child(voice)
		_players[cue] = voice

func begin(clip: StringName, clip_length: float, duration: float, drum := false) -> void:
	start_cues(CUES.get(clip, []), clip_length, duration, drum and clip in [&"reload", &"reload_empty"])

func start_cues(cues: Array, clip_length: float, duration: float, drum := false) -> void:
	stop()
	_cues = cues.duplicate(true)
	if drum:
		for cue in _cues: cue[0] = preload("res://scripts/large_drum_reload.gd").output_time(cue[0],clip_length)
		clip_length *= 1.75
	_speed = clip_length / duration if duration > 0.0 else 1.0

func advance(delta: float) -> void:
	_time += delta * _speed
	while _next < _cues.size() and _time + 0.000001 >= _cues[_next][0]:
		var cue: StringName = _cues[_next][1]
		var voice: AudioStreamPlayer = _players[cue]
		# Keep the attack intact at normal frame rates; discard stale cues after a stall.
		var late: float = (_time - _cues[_next][0]) / _speed
		if late < voice.stream.get_length():
			voice.play()
		cue_played.emit(cue, _time)
		_next += 1

func stop() -> void:
	_cues = []
	_next = 0
	_time = 0.0
	for voice: AudioStreamPlayer in _players.values():
		voice.stop()
