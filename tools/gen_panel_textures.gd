extends SceneTree
## 面板贴图族生成器（程序化，512x512 RGBA，9-slice 安全）。
## - panel_main：深灰玻璃渐变 + 45° 拉丝 + 四角金色刻线（主面板）
## - panel_inner：内嵌卡（略亮底 + 顶部高光 + 1px 边框），用于属性页/内部分区
## 运行：godot --headless --path . --script res://tools/gen_panel_textures.gd

const OUT_DIR := "res://assets/ui/textures/"
const SIZE := 512
const LATTICE := 64
const GOLD := Color(0.831, 0.686, 0.216) # THEME_GOLD #D4AF37

var _vals := PackedFloat32Array()


func _init() -> void:
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(OUT_DIR))
	var rng := RandomNumberGenerator.new()
	rng.seed = 20260809
	_vals.resize(LATTICE * LATTICE)
	for i in _vals.size():
		_vals[i] = rng.randf()
	_gen_main()
	_gen_inner()
	_gen_slot()
	_gen_tab()
	print("面板贴图已生成 -> ", ProjectSettings.globalize_path(OUT_DIR))
	quit(0)


func _v(ix: int, iy: int) -> float:
	var x := posmod(ix, LATTICE)
	var y := posmod(iy, LATTICE)
	return _vals[y * LATTICE + x]


func _smooth(t: float) -> float:
	return t * t * (3.0 - 2.0 * t)


func _noise(x: float, y: float) -> float:
	var gx := floorf(x)
	var gy := floorf(y)
	var fx := x - gx
	var fy := y - gy
	var sx := _smooth(fx)
	var sy := _smooth(fy)
	return lerpf(
		lerpf(_v(int(gx), int(gy)), _v(int(gx) + 1, int(gy)), sx),
		lerpf(_v(int(gx), int(gy) + 1), _v(int(gx) + 1, int(gy) + 1), sx),
		sy)


func _gen_main() -> void:
	var img := Image.create(SIZE, SIZE, false, Image.FORMAT_RGBA8)
	var rng := RandomNumberGenerator.new()
	rng.seed = 777
	var base_top := Color(0.078, 0.078, 0.090)   # #141417
	var base_bot := Color(0.110, 0.110, 0.125)   # #1C1C20
	for y in SIZE:
		for x in SIZE:
			var t := float(y) / float(SIZE - 1)
			var base := base_top.lerp(base_bot, t)
			# 45° 拉丝：沿 (x+y) 主方向拉伸
			var u := (float(x) + float(y)) * 0.7071
			var v := (float(x) - float(y)) * 0.7071
			var streak := _noise(u * 0.08, v * 0.55) * 0.5 + _noise(u * 0.02, v * 0.18) * 0.5
			var grain := rng.randf_range(-0.012, 0.012)
			var b := base.r + (streak - 0.5) * 0.13 + grain
			var c := Color(clampf(b, 0.0, 1.0), clampf(b, 0.0, 1.0), clampf(b * 1.02, 0.0, 1.0))
			img.set_pixel(x, y, c)
	_draw_border(img, Color(0.04, 0.04, 0.047), 1)
	_draw_corner_ticks(img)
	img.save_png(OUT_DIR + "panel_main.png")


func _gen_inner() -> void:
	var img := Image.create(SIZE, SIZE, false, Image.FORMAT_RGBA8)
	var rng := RandomNumberGenerator.new()
	rng.seed = 888
	var base_top := Color(0.129, 0.129, 0.149)   # #212126
	var base_bot := Color(0.149, 0.149, 0.172)   # #26262C
	for y in SIZE:
		for x in SIZE:
			var t := float(y) / float(SIZE - 1)
			var base := base_top.lerp(base_bot, t)
			var grain := rng.randf_range(-0.010, 0.010)
			var c := Color(
				clampf(base.r + grain, 0.0, 1.0),
				clampf(base.g + grain, 0.0, 1.0),
				clampf(base.b + grain * 1.2, 0.0, 1.0))
			img.set_pixel(x, y, c)
	# 顶部内高光（凹槽感来源）
	for x in SIZE:
		img.set_pixel(x, 1, Color(0.184, 0.184, 0.212))
		img.set_pixel(x, 2, Color(0.157, 0.157, 0.180))
	_draw_border(img, Color(0.231, 0.231, 0.259), 1)  # #3B3B42 可见细框
	_draw_border(img, Color(0.04, 0.04, 0.047), 2, 2) # 外圈暗线压边
	img.save_png(OUT_DIR + "panel_inner.png")


func _draw_border(img: Image, color: Color, thickness: int, inset := 0) -> void:
	var w := img.get_width()
	var h := img.get_height()
	for t in thickness:
		var y := inset + t
		var y2 := h - 1 - inset - t
		for x in w:
			img.set_pixel(x, y, color)
			img.set_pixel(x, y2, color)
		var x1 := inset + t
		var x2 := w - 1 - inset - t
		for yy in h:
			img.set_pixel(x1, yy, color)
			img.set_pixel(x2, yy, color)


func _draw_corner_ticks(img: Image) -> void:
	# 四角金色刻线（L 形，只落在 9-slice margin 28px 内）
	var len := 16
	var off := 8
	var thick := 2
	for corner in 4:
		var cx := off if (corner % 2 == 0) else SIZE - 1 - off - len
		var cy := off if corner < 2 else SIZE - 1 - off - len
		for i in len:
			for t in thick:
				img.set_pixel(cx + i, cy + t, GOLD)
				img.set_pixel(cx + t, cy + i, GOLD)
	# 金色细内线（距离边 26px，L 形收尾）
	var line_off := 26
	var line_len := 12
	for corner in 4:
		var cx := line_off if (corner % 2 == 0) else SIZE - 1 - line_off - line_len
		var cy := line_off if corner < 2 else SIZE - 1 - line_off - line_len
		for i in line_len:
			img.set_pixel(cx + i, cy, GOLD)
			img.set_pixel(cx, cy + i, GOLD)


func _gen_slot() -> void:
	var img := Image.create(64, 64, false, Image.FORMAT_RGBA8)
	var rng := RandomNumberGenerator.new()
	rng.seed = 999
	var base_top := Color(0.137, 0.137, 0.153)   # #232328
	var base_bot := Color(0.157, 0.157, 0.173)   # #28282C
	for y in 64:
		for x in 64:
			var t := float(y) / 63.0
			var base := base_top.lerp(base_bot, t)
			var grain := rng.randf_range(-0.012, 0.012)
			var c := Color(
				clampf(base.r + grain, 0.0, 1.0),
				clampf(base.g + grain, 0.0, 1.0),
				clampf(base.b + grain * 1.1, 0.0, 1.0))
			img.set_pixel(x, y, c)
	# 顶部内高光 + 底部内阴影（凹槽）
	for x in 64:
		img.set_pixel(x, 2, Color(0.196, 0.196, 0.216))
		img.set_pixel(x, 3, Color(0.165, 0.165, 0.184))
		img.set_pixel(x, 60, Color(0.106, 0.106, 0.122))
		img.set_pixel(x, 61, Color(0.086, 0.086, 0.10))
	_draw_border(img, Color(0.243, 0.243, 0.271), 1)   # #3E3E45 细框
	_draw_border(img, Color(0.04, 0.04, 0.047), 1, 2)  # 内压暗线
	img.save_png(OUT_DIR + "panel_slot.png")


func _gen_tab() -> void:
	var img := Image.create(128, 64, false, Image.FORMAT_RGBA8)
	var rng := RandomNumberGenerator.new()
	rng.seed = 1010
	var base_top := Color(0.114, 0.114, 0.129)   # #1D1D21
	var base_bot := Color(0.090, 0.090, 0.102)   # #17171A
	for y in 64:
		for x in 128:
			var t := float(y) / 63.0
			var base := base_top.lerp(base_bot, t)
			var grain := rng.randf_range(-0.010, 0.010)
			# 顶部金色渐变罩（0.22 alpha -> 0，25% 高度内）
			var wash := 0.0
			if y < 16:
				wash = (1.0 - float(y) / 16.0) * 0.22
			var c := Color(
				clampf(base.r + grain + GOLD.r * wash, 0.0, 1.0),
				clampf(base.g + grain + GOLD.g * wash, 0.0, 1.0),
				clampf(base.b + grain + GOLD.b * wash, 0.0, 1.0))
			img.set_pixel(x, y, c)
	# 顶边金线 + 底边金线（9-slice margin 内）
	for x in 128:
		img.set_pixel(x, 1, GOLD)
		img.set_pixel(x, 2, Color(GOLD, 0.55))
		img.set_pixel(x, 62, Color(GOLD, 0.35))
		img.set_pixel(x, 63, Color(GOLD, 0.18))
	_draw_border(img, Color(0.243, 0.243, 0.271), 1, 0)
	img.save_png(OUT_DIR + "panel_tab.png")
