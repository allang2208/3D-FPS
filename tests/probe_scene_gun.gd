extends SceneTree
## 在真实游戏场景（main.tscn）里验证枪口方向：打印模型旋转、枪口/枪托世界坐标与屏幕投影
## 运行： $godot --rendering-driver opengl3 --path 'E:\3d\3-dfps' --script res://tests/probe_scene_gun.gd

var _frames := 0
var _main: Node

func _initialize() -> void:
	var scene: PackedScene = load("res://scenes/main.tscn")
	_main = scene.instantiate()
	root.add_child(_main)

func _process(_delta: float) -> bool:
	_frames += 1
	if _frames < 5:
		return false
	var gun := root.get_node_or_null("Main/Player/Camera3D/Gun") as Node3D
	var cam := root.get_node_or_null("Main/Player/Camera3D") as Camera3D
	if gun == null or cam == null:
		print("gun/cam missing")
		quit(1)
		return false
	var model: Node3D = gun.get("_model")
	var muzzle: Vector3 = gun.get("_muzzle_local")
	print("model=", model.name, " rot_y=", model.rotation_degrees.y, " scale=", model.scale.x)
	print("muzzle_local=", muzzle)
	# 枪托：网格顶点 world z 最大（最靠近相机）
	var verts: PackedVector3Array = gun.call("_mesh_vertices", model)
	var best := Vector3.ZERO
	var best_z := -INF
	for v in verts:
		var p: Vector3 = model.global_transform * v
		if p.z > best_z:
			best_z = p.z
			best = p
	var w_muzzle: Vector3 = gun.global_transform * muzzle
	print("muzzle_world=", w_muzzle, " screen=", cam.unproject_position(w_muzzle))
	print("stock_world=", best, " screen=", cam.unproject_position(best))
	quit(0)
	return false
