extends SceneTree
## 体素风 UI 音效生成器。
## 读 ui/sound-config.json，程序化合成 WAV（方波/三角波/正弦 + 噪声 + 位深/采样率压碎），
## 输出到 assets/ui/audio/。改参数后重跑本脚本即可重新生成。
##
## 用法：godot --headless --path . --script res://tools/gen_ui_sounds.gd

const CONFIG_PATH := "res://ui/sound-config.json"
const OUT_DIR := "res://assets/ui/audio/"


func _init() -> void:
	var cfg_text := FileAccess.get_file_as_string(CONFIG_PATH)
	if cfg_text.is_empty():
		push_error("无法读取 " + CONFIG_PATH)
		quit(1)
		return
	var cfg: Dictionary = JSON.parse_string(cfg_text)
	if cfg.is_empty():
		push_error("sound-config.json 解析失败")
		quit(1)
		return

	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(OUT_DIR))
	var rate: int = cfg.get("sample_rate", 22050)
	var global_crush_rate: int = cfg.get("crush_rate", 2)
	var sounds: Dictionary = cfg.get("sounds", {})
	for name in sounds:
		var s: Dictionary = sounds[name]
		var buf := _render(name, s, rate, cfg.get("crush_bits", 8),
			s.get("crush_rate", global_crush_rate))
		var path := OUT_DIR + str(name) + ".wav"
		_write_wav(path, buf, rate)
		print("生成 ", name, ".wav  ", buf.size(), " samples / ",
			"%.0f" % (buf.size() * 1000.0 / rate), " ms")
	quit(0)


func _osc(wave: String, phase: float, rng: RandomNumberGenerator) -> float:
	match wave:
		"square":
			return 1.0 if sin(phase) >= 0.0 else -1.0
		"triangle":
			var p := fmod(phase / TAU, 1.0)
			return 4.0 * absf(p - 0.5) - 1.0
		"noise":
			return rng.randf_range(-1.0, 1.0)
		_:
			return sin(phase)


func _env(t: float, attack: float, decay: float) -> float:
	if t <= 0.0:
		return 0.0
	var a := minf(t / maxf(attack, 0.0005), 1.0)
	return a * exp(-decay * t)


func _render(name: String, s: Dictionary, rate: int, crush_bits: int, crush_rate: int) -> PackedFloat32Array:
	var wave: String = s.get("wave", "square")
	var duration: float = s.get("duration", 0.1)
	var attack: float = s.get("attack", 0.002)
	var decay: float = s.get("decay", 40.0)
	var gain: float = s.get("gain", 0.3)
	var noise: float = s.get("noise", 0.1)
	var f0: float = s.get("freq", 0.0)
	var f1: float = s.get("freq_end", f0)
	var notes: Array = s.get("notes", [])
	var rng := RandomNumberGenerator.new()
	rng.seed = name.hash()
	var n := int(duration * rate)
	var buf := PackedFloat32Array()
	buf.resize(n)

	if notes.is_empty():
		for i in n:
			var t := float(i) / float(rate)
			var freq := lerpf(f0, f1, clampf(t / maxf(duration, 0.001), 0.0, 1.0))
			var env := _env(t, attack, decay)
			var o := _osc(wave, TAU * freq * t, rng)
			var nz := rng.randf_range(-1.0, 1.0)
			buf[i] = (o * (1.0 - noise) + nz * noise) * env * gain
	else:
		var step := duration / float(notes.size()) * 0.55
		for j in notes.size():
			var start := float(j) * step
			var freq: float = float(notes[j])
			for i in n:
				var tt := float(i) / float(rate) - start
				if tt <= 0.0:
					continue
				var env := _env(tt, attack, decay)
				var o := _osc(wave, TAU * freq * tt, rng)
				var nz := rng.randf_range(-1.0, 1.0)
				buf[i] += (o * (1.0 - noise) + nz * noise) * env * gain

	# 位深压碎（量化到 crush_bits）
	if crush_bits > 0 and crush_bits < 16:
		var steps := float((1 << crush_bits) - 1)
		for i in n:
			buf[i] = roundf(buf[i] * steps) / steps
	# 采样率压碎（每 crush_rate 个样本保持一个值）
	if crush_rate > 1:
		var out := PackedFloat32Array()
		out.resize(n)
		for i in n:
			out[i] = buf[i - (i % crush_rate)]
		buf = out
	for i in n:
		buf[i] = clampf(buf[i], -1.0, 1.0)
	return buf


func _write_wav(path: String, data: PackedFloat32Array, rate: int) -> void:
	var n := data.size()
	var pcm := PackedByteArray()
	pcm.resize(n * 2)
	for i in n:
		var v := int(clampf(data[i], -1.0, 1.0) * 32767.0) & 0xFFFF
		pcm[i * 2] = v & 0xFF
		pcm[i * 2 + 1] = (v >> 8) & 0xFF
	var f := FileAccess.open(path, FileAccess.WRITE)
	if f == null:
		push_error("无法写入 " + path)
		return
	f.store_buffer("RIFF".to_ascii_buffer())
	f.store_32(36 + n * 2)
	f.store_buffer("WAVE".to_ascii_buffer())
	f.store_buffer("fmt ".to_ascii_buffer())
	f.store_32(16)
	f.store_16(1) # PCM
	f.store_16(1) # mono
	f.store_32(rate)
	f.store_32(rate * 2)
	f.store_16(2)
	f.store_16(16)
	f.store_buffer("data".to_ascii_buffer())
	f.store_32(n * 2)
	f.store_buffer(pcm)
	f.close()
