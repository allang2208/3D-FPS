extends SceneTree

# 风格化地表纹理生成：渐变 + 噪声生成低多边形手绘感贴图。
# Terrain3D 约定：albedo 的 alpha 通道存高度、normal 的 alpha 通道存粗糙度。
# 覆盖 assets/textures/terrain_prepared/ 下的同名 PNG（.import 已开 mipmap）。
# 用法：godot --headless --path <project> -s res://tools/prepare_stylized_textures.gd

const RES := 1024
const OUT_DIR := "res://assets/textures/terrain_prepared/"


func _init() -> void:
	_make("grass001", Color(0.25, 0.42, 0.20), Color(0.34, 0.54, 0.26), 0.004)
	_make("ground037", Color(0.29, 0.23, 0.17), Color(0.40, 0.33, 0.25), 0.005)
	_make("rock063", Color(0.41, 0.41, 0.43), Color(0.52, 0.52, 0.54), 0.006)
	_make("ground080", Color(0.60, 0.53, 0.38), Color(0.71, 0.64, 0.47), 0.006)
	print("[stylize] ALL TEXTURES PREPARED")
	quit(0)


func _make(asset_name: String, c0: Color, c1: Color, freq: float) -> void:
	var fnl := FastNoiseLite.new()
	fnl.frequency = freq
	fnl.fractal_octaves = 3

	# albedo + 高度（alpha 存噪声值）
	var alb := Image.create_empty(RES, RES, false, Image.FORMAT_RGBA8)
	for x in alb.get_width():
		for y in alb.get_height():
			var n := fnl.get_noise_2d(x, y) * 0.5 + 0.5
			var c := c0.lerp(c1, n)
			c.a = n
			alb.set_pixel(x, y, c)
	alb.save_png(OUT_DIR + asset_name + "_alb_ht.png")

	# normal（噪声梯度近似）+ 粗糙度（alpha 固定 0.85）
	var nrm := Image.create_empty(RES, RES, false, Image.FORMAT_RGBA8)
	for x in nrm.get_width():
		for y in nrm.get_height():
			var h0 := fnl.get_noise_2d(x, y)
			var hx := fnl.get_noise_2d(x + 2, y)
			var hy := fnl.get_noise_2d(x, y + 2)
			var nx := h0 - hx
			var ny := h0 - hy
			var len := sqrt(nx * nx + ny * ny + 1.0)
			var c := Color(nx / len * 0.5 + 0.5, ny / len * 0.5 + 0.5, 1.0, 0.85)
			nrm.set_pixel(x, y, c)
	nrm.save_png(OUT_DIR + asset_name + "_nrm_rgh.png")
