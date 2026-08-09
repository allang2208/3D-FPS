extends SceneTree
## 决定性方向验证：在枪口放红球、枪托末端放蓝球，渲染后从画面定位两球
## 红球应在画面左侧（远处）、蓝球在右侧（近处）→ 枪口朝前
## 运行： $godot --rendering-driver opengl3 --path 'E:\3d\3-dfps' --script res://tests/render_gun_markers.gd

var _frames := 0
var _gun: Node3D

func _process(_delta: float) -> bool:
	_frames += 1
	if _frames == 1:
		var cam := Camera3D.new()
		cam.name = "Cam"
		cam.fov = 75.0
		root.add_child(cam)
		cam.make_current()
		var gun := Node3D.new()
		gun.name = "Gun"
		gun.position = Vector3(0.28, -0.26, -0.5)
		gun.set_script(load("res://scripts/gun.gd"))
		cam.add_child(gun)
		_gun = gun
	if _frames == 3:
		_place_markers()
	if _frames == 15:
		var img := root.get_viewport().get_texture().get_image()
		if img != null and img.get_width() > 0:
			var out := "user://gun_markers.png"
			img.save_png(out)
			print("SAVED ", ProjectSettings.globalize_path(out))
		quit(0)
		return false
	return false

func _place_markers() -> void:
	var gun_space_of := func(p: Vector3) -> Vector3:
		return _gun.global_transform * p
	# 红球：枪口
	var muzzle: Vector3 = _gun.get("_muzzle_local")
	_add_sphere(gun_space_of.call(muzzle), Color(1, 0, 0, 1), "MuzzleMark")
	# 蓝球：枪托末端 = 网格顶点中 gun-space z 最大（最靠近相机）的点
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
	print("muzzle_gun=", muzzle, " -> world=", gun_space_of.call(muzzle))
	print("stock_world=(z max)=", best, " z=", best_z)

func _add_sphere(world: Vector3, col: Color, name: String) -> void:
	var mi := MeshInstance3D.new()
	mi.name = name
	var s := SphereMesh.new()
	s.radius = 0.025
	s.height = 0.05
	var mat := StandardMaterial3D.new()
	mat.albedo_color = col
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	s.material = mat
	mi.mesh = s
	mi.global_position = world
	root.add_child(mi)
