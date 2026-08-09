extends SceneTree
## ADS 自动校准回归：挂载 Gun 节点（不依赖 UI 场景）
## 验证：枪口朝 -Z、照门/准星落在相机光轴上、无网格穿透相机近平面
## 运行： $godot --headless --path 'E:\3d\3-dfps' --script res://tests/test_ads_calibration.gd

var _frames := 0
var _gun: Node3D
var _fails: Array[String] = []

func _process(_delta: float) -> bool:
	_frames += 1
	if _frames == 1:
		var cam := Camera3D.new()
		cam.name = "Cam"
		root.add_child(cam)
		var gun := Node3D.new()
		gun.name = "Gun"
		gun.set_script(load("res://scripts/gun.gd"))
		var model_path := OS.get_environment("GUN_TEST_MODEL")
		if model_path != "":
			gun.set("model_scene", load(model_path))
			print("TEST model_scene=", model_path)
		cam.add_child(gun)
		_gun = gun
	if _frames < 2:
		return false
	_check()
	for f in _fails:
		print("FAIL ", f)
	print("TEST ads_calibration=", _fails.is_empty())
	quit(0 if _fails.is_empty() else 1)
	return false

func _check() -> void:
	var model: Node3D = _gun.get("_model")
	var rot_y: float = model.rotation_degrees.y
	var scale: float = model.scale.x
	var muzzle: Vector3 = _gun.get("_muzzle_local")
	var ads_pos: Vector3 = _gun.get("_ads_pos")
	var ads_rot: Vector3 = _gun.get("_ads_rot")
	var rear: Vector3 = _gun.get("_sight_rear")
	var front: Vector3 = _gun.get("_sight_front")
	var rear_dist: float = _gun.get("_rear_dist")
	print("rot_y=", rot_y, " scale=", scale)
	print("muzzle_local=", muzzle)
	print("ads_pos=", ads_pos, " ads_rot=", ads_rot, " rear_dist=", rear_dist)
	print("rear=", rear, " front=", front)
	print("mag_pos=", _gun.get("_mag").position, " mag_base_y=", _gun.get("_mag_base_y"))
	# 1. 枪口朝前（-Z）：允许 rot_y=±90（依枪模枪口朝向而定）
	if absf(absf(rot_y) - 90.0) > 1.0:
		_fails.append("muzzle axis not Z: rot_y=" + str(rot_y))
	if muzzle.z > -0.2:
		_fails.append("muzzle not forward: " + str(muzzle))
	# 2. ADS 后照门/准星落在相机光轴
	var basis := Basis.from_euler(ads_rot)
	var w_rear := ads_pos + basis * rear
	var d: Vector3 = front - rear
	var w_front := ads_pos + basis * front
	if absf(w_rear.x) > 0.008 or absf(w_rear.y) > 0.008:
		_fails.append("rear not on camera axis: " + str(w_rear))
	if absf(w_rear.z + rear_dist) > 0.01:
		_fails.append("rear dist wrong: " + str(w_rear))
	if absf(w_front.x) > 0.008 or absf(w_front.y) > 0.008:
		_fails.append("front not on camera axis: " + str(w_front))
	if absf(w_front.z - (w_rear.z - d.length())) > 0.015:
		_fails.append("front dist wrong: " + str(w_front))
	# 3. 无网格穿透相机近平面（相机空间 z <= -0.04）
	var min_z := INF
	var verts: PackedVector3Array = _gun.call("_mesh_vertices", model)
	var akm_basis := model.global_transform.basis * Basis.from_euler(Vector3(0, deg_to_rad(rot_y), 0))
	var akm_scale := scale
	for v in verts:
		var p: Vector3 = akm_basis * (v * akm_scale)
		var w := ads_pos + basis * p
		min_z = minf(min_z, w.z)
	print("min_mesh_z_in_ads=", min_z)
	if min_z > -0.04:
		_fails.append("mesh penetrates near plane: min_z=" + str(min_z))
