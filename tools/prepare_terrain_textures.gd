extends SceneTree

# One-shot prep: pack AmbientCG PBR maps into Terrain3D channel textures.
# Convention: albedo.alpha = height, normal.alpha = roughness.
# - Prefers {name}-4k/{name}_4K-JPG_*.jpg source, falls back to 2K.
# - Terrain3D requires ALL texture sets at identical resolution, so RES
#   must be uniform (4096 here, matching the existing 5 four-K sets).
# Usage: godot --headless --path <project> -s res://tools/prepare_terrain_textures.gd

const RES := 4096
const SRC_4K := "res://assets/textures/terrain/%s-4k/%s_4K-JPG_%s.jpg"
const SRC_2K := "res://assets/textures/terrain/%s/%s_2K-JPG_%s.jpg"
const OUT_DIR := "res://assets/textures/terrain_prepared/"

# Surface sets: grass / moss grass / fresh grass / short grass / forest floor /
# gravel / dirt / sand / rock. Keep order in sync with demo_terrain.gd tex_ids.
var names := ["Grass001", "Grass004", "Grass005", "Grass007",
	"Ground020", "Ground030", "Ground037", "Ground080", "Rock063"]


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
	var alb_src := SRC_4K % [folder, name, "Color"]
	if not FileAccess.file_exists(alb_src):
		alb_src = SRC_2K % [folder, name, "Color"]
		print("[prepare] %s: no 4K source, fallback 2K" % name)
	var alb := Image.load_from_file(alb_src)
	var hgt_src := SRC_4K % [folder, name, "Displacement"]
	if not FileAccess.file_exists(hgt_src):
		hgt_src = SRC_2K % [folder, name, "Displacement"]
	var hgt := Image.load_from_file(hgt_src)
	alb.resize(RES, RES)
	hgt.resize(RES, RES)
	# Pitfall: JPG loads as RGB8; writing alpha without RGBA8 gets dropped on
	# save_png. Convert first so height really lands in the alpha channel.
	alb.convert(Image.FORMAT_RGBA8)
	for x in alb.get_width():
		for y in alb.get_height():
			var c := alb.get_pixel(x, y)
			c.a = hgt.get_pixel(x, y).v
			alb.set_pixel(x, y, c)
	alb.save_png(OUT_DIR + folder + "_alb_ht.png")


func _prepare_normal(folder: String, name: String) -> void:
	var nrm_src := SRC_4K % [folder, name, "NormalGL"]
	if not FileAccess.file_exists(nrm_src):
		nrm_src = SRC_2K % [folder, name, "NormalGL"]
	var nrm := Image.load_from_file(nrm_src)
	var rgh_src := SRC_4K % [folder, name, "Roughness"]
	if not FileAccess.file_exists(rgh_src):
		rgh_src = SRC_2K % [folder, name, "Roughness"]
	var rgh := Image.load_from_file(rgh_src)
	nrm.resize(RES, RES)
	rgh.resize(RES, RES)
	nrm.convert(Image.FORMAT_RGBA8)
	for x in nrm.get_width():
		for y in nrm.get_height():
			var c := nrm.get_pixel(x, y)
			c.a = rgh.get_pixel(x, y).v
			nrm.set_pixel(x, y, c)
	nrm.save_png(OUT_DIR + folder + "_nrm_rgh.png")
