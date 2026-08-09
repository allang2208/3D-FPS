extends Node
## 体素风 UI 音效入口：预加载 tools/gen_ui_sounds.gd 合成的 WAV，
## 通过 AudioManager 池播放（互不切断）。音量偏移集中在这里微调。
## 音色参数在 ui/sound-config.json，改后重跑生成器即可。

const HOVER := preload("res://assets/ui/audio/hover.wav")
const CLICK := preload("res://assets/ui/audio/click.wav")
const SWITCH_ON := preload("res://assets/ui/audio/switch_on.wav")
const SWITCH_OFF := preload("res://assets/ui/audio/switch_off.wav")
const CONFIRM := preload("res://assets/ui/audio/confirm.wav")
const CANCEL := preload("res://assets/ui/audio/cancel.wav")


static func hover() -> void:
	_play(HOVER, -8.0)


static func click() -> void:
	_play(CLICK, -2.0)


static func switch_on() -> void:
	_play(SWITCH_ON, -3.0)


static func switch_off() -> void:
	_play(SWITCH_OFF, -3.0)


static func confirm() -> void:
	_play(CONFIRM, -2.0)


static func cancel() -> void:
	_play(CANCEL, -3.0)


static func _play(stream: AudioStream, volume_db: float) -> void:
	if stream == null:
		return
	var tree := Engine.get_main_loop() as SceneTree
	if tree == null:
		return
	var am := tree.root.get_node_or_null("AudioManager")
	if am != null and am.has_method("play_sfx"):
		am.play_sfx(stream, volume_db)
