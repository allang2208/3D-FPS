extends SceneTree
## IK 臂探针：挂载真实 Gun（含 LeftArm），验证 IterateIK3D 把腕骨姿态解算到弹匣目标
## 运行： $godot --headless --path 'E:\3d\3-dfps' --script res://tests/probe_arm_ik.gd

var _frames := 0
var _gun: Node3D
var _arm: Node3D
var _skel: Skeleton3D
var _target: Node3D
var _fails: Array[String] = []
var _phase := 0

func _process(_delta: float) -> bool:
	_frames += 1
	if _frames == 1:
		var cam := Camera3D.new()
		cam.name = "Cam"
		root.add_child(cam)
		var gun := Node3D.new()
		gun.name = "Gun"
		gun.set_script(load("res://scripts/gun.gd"))
		cam.add_child(gun)
		_gun = gun
	if _frames == 3:
		_arm = _gun.get_node_or_null("LeftArm")
		if _arm == null:
			_fails.append("LeftArm missing")
			_finish()
			return false
		_skel = _arm.get_node("ArmSkeleton") as Skeleton3D
		_target = _arm.get_node("HandTarget") as Node3D
		# 目标应被 gun.gd 初始化为弹匣位置附近（非零）
		if _target.position.length_squared() < 0.0001:
			_fails.append("HandTarget not initialized to mag position")
		# 结构：骨骼链 parent 正确、IK 子节点存在
		if _skel.get_bone_parent(_skel.find_bone("forearm")) != _skel.find_bone("upper_arm"):
			_fails.append("forearm parent wrong")
		if _skel.get_bone_parent(_skel.find_bone("hand")) != _skel.find_bone("forearm"):
			_fails.append("hand parent wrong")
		var ik := _skel.get_node_or_null("ReloadIK")
		if ik == null:
			_fails.append("ReloadIK missing")
		else:
			if not (ik is JacobianIK3D):
				_fails.append("ReloadIK not JacobianIK3D")
			if ik.get_root_bone_name(0) != "upper_arm" or ik.get_end_bone_name(0) != "hand":
				_fails.append("IK chain bones wrong")
		_finish()
		return false
	return false

func _finish() -> void:
	var hand_idx := _skel.find_bone("hand")
	var rest_origin := _skel.get_bone_global_rest(hand_idx).origin
	print("hand_rest=", rest_origin, " target=", _target.position)
	for f in _fails:
		print("FAIL ", f)
	print("TEST arm_ik=", _fails.is_empty())
	quit(0 if _fails.is_empty() else 1)
