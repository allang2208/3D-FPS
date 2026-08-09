extends SceneTree

# 一次性准备脚本：把 AmbientCG 的 PBR 贴图打包成 Terrain3D 专用纹理。
# Terrain3D 约定：albedo 的 alpha 通道存高度，normal 的 alpha 通道存粗糙度。
# 用法：godot --headless --path <project> -s res://tools/prepare_terrain_textures.gd

const RES := 1024
const SRC := "res://assets/textures/terrain/%s/%s_2K-JPG_%s.jpg"
const OUT_DIR := "res://assets/textures/terrain_prepared/"

var names := ["Grass001", "Ground037", "Rock063", "Ground080"]


func _init() -> void:
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(OUT_DIR))
	for n: String in names:
		var folder := n.to_lower()
		_prepare_albedo(folder, n)
		_prepare_normal(folder, n)
		print("[prepare] %s done" % n)
	print("[prepare] ALL TEXTURES PREPARED")
	quit(0)


func _prepare_albedo(folder: String, name: String) -> void:
	var alb := Image.load_from_file(SRC % [folder, name, "Color"])
	var hgt := Image.load_from_file(SRC % [folder, name, "Displacement"])
	alb.resize(RES, RES)
	hgt.resize(RES, RES)
	for x in alb.get_width():
		for y in alb.get_height():
			var c := alb.get_pixel(x, y)
			c.a = hgt.get_pixel(x, y).v
			alb.set_pixel(x, y, c)
	alb.save_png(OUT_DIR + folder + "_alb_ht.png")


func _prepare_normal(folder: String, name: String) -> void:
	var nrm := Image.load_from_file(SRC % [folder, name, "NormalGL"])
	var rgh := Image.load_from_file(SRC % [folder, name, "Roughness"])
	nrm.resize(RES, RES)
	rgh.resize(RES, RES)
	for x in nrm.get_width():
		for y in nrm.get_height():
			var c := nrm.get_pixel(x, y)
			c.a = rgh.get_pixel(x, y).v
			nrm.set_pixel(x, y, c)
	nrm.save_png(OUT_DIR + folder + "_nrm_rgh.png")
