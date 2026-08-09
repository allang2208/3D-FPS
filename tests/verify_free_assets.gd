extends SceneTree

# 一次性验证：2026-08-09 批量下载的 CC0 资产可被 Godot 正常加载。

func _init() -> void:
	var fails: Array[String] = []

	# 统计各类资产数量
	var terrain_tex_count := _count_files("res://assets/textures/terrain", ["jpg", "png"])
	var polyhaven_gltf := _count_files("res://assets/models/polyhaven", ["gltf"])
	var kenney_nature_glb := _count_files("res://assets/models/kenney_nature", ["glb"])
	var kenney_td_glb := _count_files("res://assets/models/kenney_tower_defense", ["glb"])
	print("[verify] textures=", terrain_tex_count, " polyhaven_gltf=", polyhaven_gltf,
		" nature_glb=", kenney_nature_glb, " towerdef_glb=", kenney_td_glb)

	# 逐个加载代表性资源
	var samples := {
		"rock_07.gltf": "res://assets/models/polyhaven/rock_07/rock_07_2k.gltf",
		"grass_color.jpg": "res://assets/textures/terrain/grass001/Grass001_2K-JPG_Color.jpg",
		"nature_cactus.glb": "res://assets/models/kenney_nature/cactus_tall.glb",
		"td_wood_structure.glb": _first_glb("res://assets/models/kenney_tower_defense", "wood-structure"),
		"hdri.hdr": "res://assets/environment/hdri/kloofendal_48d_partly_cloudy_puresky_2k.hdr",
	}
	for key: String in samples:
		var path: String = samples[key]
		if path.is_empty():
			fails.append("%s -> no file matched" % key)
			continue
		var res := load(path)
		if res == null:
			fails.append("%s -> load failed: %s" % [key, path])
		else:
			print("[verify] OK %s -> %s (%s)" % [key, path, res.get_class()])

	if fails.is_empty():
		print("[verify] ALL ASSETS OK")
		quit(0)
	else:
		for f in fails:
			push_error(f)
		quit(1)


func _count_files(dir_path: String, exts: Array[String]) -> int:
	var count := 0
	var dir := DirAccess.open(dir_path)
	if dir == null:
		return 0
	dir.list_dir_begin()
	var f := dir.get_next()
	while f != "":
		var p := dir_path.path_join(f)
		if dir.current_is_dir():
			if f != "." and f != "..":
				count += _count_files(p, exts)
		elif f.get_extension().to_lower() in exts:
			count += 1
		f = dir.get_next()
	return count


func _first_glb(dir_path: String, keyword: String) -> String:
	var dir := DirAccess.open(dir_path)
	if dir == null:
		return ""
	dir.list_dir_begin()
	var f := dir.get_next()
	while f != "":
		if not dir.current_is_dir() and f.to_lower().contains(keyword) and f.ends_with(".glb"):
			return dir_path.path_join(f)
		f = dir.get_next()
	return ""
