extends SceneTree

# 渲染地形地面特写：草地/泥土/岩石 三张，供 GLM 与实例图对比分析
# 运行：& $godot --rendering-driver opengl3 --path 'E:\3d\3-dfps' --script res://tests/render_terrain_ground.gd

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
		if _cam != null:
			# camera_fx 每帧覆盖相机旋转，会吞掉 look_at；渲染地面特写时先停用它
			var cfx := _cam.get_node_or_null("CameraFx") as Node
			if cfx != null:
				cfx.set_script(null)
				cfx.set_physics_process(false)
				cfx.set_process(false)
	if _frames < 20:
		return false
	var img := root.get_viewport().get_texture().get_image()
	if img == null or img.get_width() == 0:
		print("VIEWPORT EMPTY")
		quit(0)
		return false
	var out := "user://terrain_ground_%d.png" % _shots
	img.save_png(out)
	print("SAVED ", ProjectSettings.globalize_path(out), " at=", _player.global_position)
	_shots += 1
	if _shots >= 3:
		quit(0)
		return false
	_advance()
	return false


func _advance() -> void:
	if _cam == null or _terrain == null:
		return
	var spots := [Vector3(35, 0, 15), Vector3(-120, 0, -60), Vector3(120, 0, -260)]
	if _shots - 1 < spots.size():
		var s: Vector3 = spots[_shots - 1]
		var h := _terrain.data.get_height(s)
		_player.global_position = Vector3(s.x, h + 3.0, s.z)
		# 垂直俯视正下方地面（确保画面中心就是地形，不掺天空）
		_cam.look_at(Vector3(s.x, h - 1.0, s.z), Vector3.FORWARD)
		print("[cam] shot=", _shots, " rot=", _cam.rotation_degrees, " pos=", _cam.global_position)
