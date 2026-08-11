extends SceneTree

# 地形场景渲染检查：加载旷野场景，等 Terrain3D LOD / 粒子草就绪后截图到 user://terrain_check.png。
# 运行： $godot --path 'E:\3d\3-dfps' --script res://tests/render_terrain_check.gd

var _frames := 0
var _loaded := false


func _init() -> void:
	process_frame.connect(_on_frame)


func _on_frame() -> void:
	# 延迟到第一帧再加载：-s 模式下 autoload（HUD）在 _init 时尚未注册。
	if not _loaded:
		_loaded = true
		var scene: Node = load("res://scenes/demo_terrain.tscn").instantiate()
		root.add_child(scene)
		current_scene = scene
		return
	_frames += 1
	if _frames == 60:
		_save("user://terrain_check.png")
		quit(0)


func _save(path: String) -> void:
	var img := root.get_viewport().get_texture().get_image()
	if img == null or img.get_width() == 0:
		print("EMPTY at ", path)
		return
	img.save_png(path)
	print("SAVED ", ProjectSettings.globalize_path(path))
