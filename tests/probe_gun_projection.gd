extends SceneTree
## 在游戏相机下打印枪口/枪托/瞄具的世界坐标与屏幕投影，对比两版模型朝向
## 运行： $env:PROBE_GLB='res://assets/models/akm_trellis.glb'; $godot --headless --path 'E:\3d\3-dfps' --script res://tests/probe_gun_projection.gd

var _frames := 0
var _gun: Node3D
var _cam: Camera3D

func _process(_delta: float) -> bool:
	_frames += 1
	if _frames == 1:
		_cam = Camera3D.new()
		_cam.name = "Cam"
		_cam.fov = 75.0
		root.add_child(_cam)
		_cam.make_current()
		var gun := Node3D.new()
		gun.name = "Gun"
		gun.position = Vector3(0.28, -0.26, -0.5)
		gun.set_script(load("res://scripts/gun.gd"))
		var model_path := OS.get_environment("PROBE_GLB")
		if model_path != "":
			gun.set("model_scene", load(model_path))
		_cam.add_child(gun)
		_gun = gun
	if _frames < 3:
		return false
	# 枪节点姿态：腰射（0）与机瞄（_ads_rot）都打
	var muzzle: Vector3 = _gun.get("_muzzle_local")
	var rear: Vector3 = _gun.get("_sight_rear")
	var front: Vector3 = _gun.get("_sight_front")
	var ads_pos: Vector3 = _gun.get("_ads_pos")
	var ads_rot: Vector3 = _gun.get("_ads_rot")
	var scale: float = _gun.get("_model").scale.x
	var rot_y: float = _gun.get("_model").rotation_degrees.y
	print("model rot_y=", rot_y, " scale=", scale)
	for pose_name in ["hip", "ads"]:
		_gun.position = Vector3(0.28, -0.26, -0.5) if pose_name == "hip" else ads_pos
		_gun.rotation = Vector3.ZERO if pose_name == "hip" else ads_rot
		for tag in ["muzzle", "rear", "front"]:
			var p: Vector3 = muzzle if tag == "muzzle" else (rear if tag == "rear" else front)
			var world: Vector3 = _gun.global_transform * p
			var s := _cam.unproject_position(world)
			print(pose_name, " ", tag, " local=", p, " world=", world, " screen=", s)
	quit(0)
	return false
