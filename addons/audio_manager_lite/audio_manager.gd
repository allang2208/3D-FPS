extends Node
## AudioManager Lite — autoload singleton (free).
## One-line SFX playback with a small pool (sounds never cut each other off),
## basic music with stop/resume, and per-bus volume saved to disk.
##
## Upgrade path: drop in Audio Manager PRO — same autoload name, seamless.

signal music_changed(stream: AudioStream)
signal sfx_played(stream: AudioStream)

const SETTINGS_PATH := "user://audio.cfg"
const BUSES := ["Master", "Music", "SFX"]
const SILENCE_DB := -80.0

@export var sfx_pool_size: int = 8

var volumes: Dictionary = {"Master": 1.0, "Music": 1.0, "SFX": 1.0}

var _sfx_pool: Array[AudioStreamPlayer] = []
var _music_player: AudioStreamPlayer
var _sfx_bus := "SFX"
var _music_bus := "Music"


func _ready() -> void:
	if AudioServer.get_bus_index("SFX") < 0:
		_sfx_bus = "Master"
	if AudioServer.get_bus_index("Music") < 0:
		_music_bus = "Master"
	for i in sfx_pool_size:
		_sfx_pool.append(_make_player(_sfx_bus))
	_music_player = _make_player(_music_bus)
	load_settings()
	for bus in BUSES:
		_apply_volume(bus)


# ---------------------------------------------------------------- SFX
## Play a one-shot SFX. Never cuts off a sound already playing.
func play_sfx(stream: AudioStream, volume_db: float = 0.0) -> AudioStreamPlayer:
	if stream == null:
		return null
	var p := _free_player()
	p.stream = stream
	p.volume_db = volume_db
	p.play()
	sfx_played.emit(stream)
	return p


# ---------------------------------------------------------------- music
func play_music(stream: AudioStream) -> void:
	if stream == null:
		return
	_music_player.stream = stream
	_music_player.play()
	music_changed.emit(stream)


func stop_music() -> void:
	_music_player.stop()


func is_music_playing() -> bool:
	return _music_player.playing


# ---------------------------------------------------------------- volume
func set_volume(bus: String, linear: float) -> void:
	volumes[bus] = clampf(linear, 0.0, 1.0)
	_apply_volume(bus)


func set_master_volume(v: float) -> void: set_volume("Master", v)
func set_music_volume(v: float) -> void:  set_volume("Music", v)
func set_sfx_volume(v: float) -> void:    set_volume("SFX", v)
func get_volume(bus: String) -> float:    return volumes.get(bus, 1.0)


# ---------------------------------------------------------------- persistence
func save_settings() -> void:
	var cfg := ConfigFile.new()
	for bus in BUSES:
		cfg.set_value("audio", bus, volumes.get(bus, 1.0))
	cfg.save(SETTINGS_PATH)


func load_settings() -> void:
	var cfg := ConfigFile.new()
	if cfg.load(SETTINGS_PATH) != OK:
		return
	for bus in BUSES:
		volumes[bus] = clampf(cfg.get_value("audio", bus, volumes.get(bus, 1.0)), 0.0, 1.0)


# ---------------------------------------------------------------- internals
func _make_player(bus: String) -> AudioStreamPlayer:
	var p := AudioStreamPlayer.new()
	p.bus = bus
	add_child(p)
	return p


func _free_player() -> AudioStreamPlayer:
	for p in _sfx_pool:
		if not p.playing:
			return p
	var np := _make_player(_sfx_bus)
	_sfx_pool.append(np)
	return np


func _apply_volume(bus: String) -> void:
	var idx := AudioServer.get_bus_index(bus)
	if idx < 0:
		return
	AudioServer.set_bus_volume_db(idx, linear_to_db(maxf(volumes.get(bus, 1.0), 0.0001)))
