extends SceneTree
## 程序化生成 UI 纹理（不依赖生图模型/余额）：深灰磨砂金属拉丝面板底纹，无缝。
## 运行： $godot --headless --path 'E:\3d\3-dfps' --script res://tools/gen_ui_textures.gd

const OUT := "res://assets/ui/textures/panel_brushed.png"
const SIZE := 512

func _hash2(x: int, y: int) -> float:
	var n := x * 374761393 + y * 668265263
	n = (n ^ (n >> 13)) * 1274126177
	return float((n & 0xFFFFFF)) / 16777215.0

func _initialize() -> void:
	var img := Image.create(SIZE, SIZE, false, Image.FORMAT_RGBA8)
	var base := Color(0.102, 0.102, 0.11)  # ~#1A1A1C 深灰
	img.fill(base)
	for y in SIZE:
		# 水平拉丝：行间低频明暗（横向一致 → 水平纹理）
		var line := sin(float(y) * 0.06) * 0.012 + (_hash2(0, y) - 0.5) * 0.02
		for x in SIZE:
			var n := (_hash2(x, y) - 0.5) * 0.016
			var v := clampf(base.r + line + n, 0.0, 1.0)
			img.set_pixel(x, y, Color(v, v, v, 1.0))
	img.save_png(OUT)
	print("saved ", OUT)
	quit()
