extends SceneTree

const Sound := preload("res://ui/sound.gd")
const NAMES := ["hover", "click", "switch_on", "switch_off", "confirm", "cancel"]


func _initialize() -> void:
	var fail := 0
	var cfg: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://ui/sound-config.json"))
	var sounds: Dictionary = cfg.get("sounds", {})
	for name in NAMES:
		var path := "res://assets/ui/audio/%s.wav" % name
		if not ResourceLoader.exists(path):
			push_error("缺少音效: " + path)
			fail += 1
			continue
		var wav := load(path) as AudioStreamWAV
		if wav == null:
			push_error("音效加载失败: " + path)
			fail += 1
			continue
		if wav.data.is_empty():
			push_error("音效数据为空: " + path)
			fail += 1
			continue
		var dur_ms := float(sounds.get(name, {}).get("duration", 0.0)) * 1000.0
		print("%s.wav  %d ms (config)  mix_rate=%d" % [name, int(dur_ms), wav.mix_rate])

	var am: Node = root.get_node_or_null("AudioManager")
	print("AudioManager autoload: ", am != null)
	if am == null:
		fail += 1
	process_frame.connect(func() -> void:
		if am != null:
			# 冒烟测试：每个播放入口都不报错（首帧后播放器池已入树）
			Sound.hover()
			Sound.click()
			Sound.switch_on()
			Sound.switch_off()
			Sound.confirm()
			Sound.cancel()
			print("播放入口调用 OK")
		quit(1 if fail > 0 else 0))
