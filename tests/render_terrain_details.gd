extends SceneTree

# 渲染地形细节实拍照：出生点环视 + 林下植被特写
# 运行：& $godot --rendering-driver opengl3 --path 'E:\3d\3-dfps' --script res://tests/render_terrain_details.gd

var _scene: Node
var _frames := 0
var _shots := 0
var _cam: Camera3D
var _player: Node3D
var _terrain: Terrain3D


func _initialize() -> void:
	_scene = load("res://scenes/demo_terrain.tscn").instantiate()
	root.add_child(_scene)


func _process(_delta: float) -> bool:
	_frames += 1
	if _player == null:
		_player = _scene.get_node_or_null("Player") as Node3D
		_terrain = _scene.get_node_or_null("Terrain3D") as Terrain3D
	if _player != null and _cam == null:
		_cam = _player.get_node_or_null("Camera3D") as Camera3D
	if _frames < 20:
		return false
	var viewport := root.get_viewport()
	var img := viewport.get_texture().get_image()
	if img == null or img.get_width() == 0:
		print("VIEWPORT EMPTY, frames=", _frames)
		quit(0)
		return false
	var out := "user://terrain_detail_%d.png" % _shots
	img.save_png(out)
	print("SAVED ", ProjectSettings.globalize_path(out), " cam_pos=", _cam.global_position if _cam else "?")
	_shots += 1
	if _shots >= 4:
		quit(0)
		return false
	_advance_camera()
	return false


func _advance_camera() -> void:
	if _cam == null or _terrain == null:
		return
	var targets := [
		Vector3(-60, 0, -30),   # 西侧林下植被
		Vector3(120, 0, 60),    # 东南树丛
		Vector3(40, 0, -120),   # 北侧竹林/蕨类带
	]
	if _shots - 1 < targets.size():
		var t: Vector3 = targets[_shots - 1]
		var h := _terrain.data.get_height(t)
		_player.global_position = Vector3(t.x, h + 2.0, t.z)
