extends SceneTree
## 侧视方向判定：相机在枪侧面，枪长横贯画面；红球=校准枪口、蓝球=校准枪托
## 判定：枪口端应细（枪管/制退器），枪托端应粗（枪托）
## 运行： $godot --rendering-driver opengl3 --path 'E:\3d\3-dfps' --script res://tests/render_gun_side_markers.gd

var _frames := 0
var _gun: Node3D
var _cam: Camera3D

func _process(_delta: float) -> bool:
	_frames += 1
	if _frames == 1:
		_cam = Camera3D.new()
		_cam.name = "SideCam"
		_cam.fov = 60.0
		root.add_child(_cam)
		_cam.make_current()
		var gun := Node3D.new()
		gun.name = "Gun"
		gun.position = Vector3(0.28, -0.26, -0.5)
		gun.set_script(load("res://scripts/gun.gd"))
		_cam.add_child(gun)
		_gun = gun
	if _frames == 3:
		# 先摆相机（枪是相机子节点，会跟着动），再算标记
		_cam.global_position = Vector3(1.6, -0.13, -0.8)
		_cam.look_at(Vector3(0.3, -0.13, -0.8), Vector3.UP)
		_place()
	if _frames == 15:
		var img := root.get_viewport().get_texture().get_image()
		if img != null and img.get_width() > 0:
			var out := "user://gun_side_markers.png"
			img.save_png(out)
			print("SAVED ", ProjectSettings.globalize_path(out))
		quit(0)
		return false
	return false

func _place() -> void:
	var muzzle: Vector3 = _gun.get("_muzzle_local")
	var w_muzzle: Vector3 = _gun.global_transform * muzzle
	_add_sphere(w_muzzle, Color(1, 0, 0, 1), "MuzzleMark")
	var model: Node3D = _gun.get("_model")
	var verts: PackedVector3Array = _gun.call("_mesh_vertices", model)
	var best := Vector3.ZERO
	var best_z := -INF
	for v in verts:
		var p: Vector3 = model.global_transform * v
		if p.z > best_z:
			best_z = p.z
			best = p
	_add_sphere(best, Color(0, 0, 1, 1), "StockMark")
	print("muzzle_world=", w_muzzle, " stock_world=", best)

func _add_sphere(world: Vector3, col: Color, name: String) -> void:
	var mi := MeshInstance3D.new()
	mi.name = name
	var s := SphereMesh.new()
	s.radius = 0.03
	s.height = 0.06
	var mat := StandardMaterial3D.new()
	mat.albedo_color = col
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	s.material = mat
	mi.mesh = s
	mi.global_position = world
	root.add_child(mi)
