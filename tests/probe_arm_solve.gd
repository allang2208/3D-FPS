extends SceneTree
## IK 左臂回归测试（渲染模式）：验证 JacobianIK3D 把手骨解算向目标旋转
## 注意：modifier 写入只进蒙皮矩阵，骨骼 pose 会被恢复，必须用 modification_processed 信号在解算瞬间观测
## 运行：$godot --rendering-driver opengl3 --path 'E:\3d\3-dfps' --script res://tests/probe_arm_solve.gd

var _frames := 0
var _skel: Skeleton3D
var _target: Node3D
var _ik: JacobianIK3D
var _max_rot := 0.0
var _fails: Array[String] = []

func _process(_delta: float) -> bool:
	_frames += 1
	if _frames == 1:
		var cam := Camera3D.new()
		cam.name = "Cam"
		root.add_child(cam)
		cam.make_current()
		var gun := Node3D.new()
		gun.name = "Gun"
		cam.add_child(gun)
		var arm := Node3D.new()
		arm.name = "LeftArm"
		arm.set_script(load("res://scripts/viewmodel_arms.gd"))
		gun.add_child(arm)
		_skel = arm.get_node("ArmSkeleton") as Skeleton3D
		_target = arm.get_node("HandTarget") as Node3D
		_ik = arm.get_node("ArmSkeleton/ReloadIK") as JacobianIK3D
		_ik.modification_processed.connect(_on_mod_processed)
		# 全局姿态缓存必须已初始化，否则 IK 链坐标为原点
		if _skel.get_bone_global_pose(_skel.find_bone("hand")).origin.is_zero_approx():
			_fails.append("global pose cache not initialized (reset_bone_poses missing)")
		if _ik == null:
			_fails.append("ReloadIK missing or not JacobianIK3D")
		elif _ik.get_joint_count(0) != 3:
			_fails.append("joint count != 3")
	if _frames == 6:
		_target.position = Vector3(0.42, 0.35, -0.25)  # 远目标，迫使大幅旋转
	if _frames == 16:
		_finish()
		return false
	return false

func _on_mod_processed() -> void:
	var ru: float = _skel.get_bone_pose_rotation(_skel.find_bone("upper_arm")).get_angle()
	var rf: float = _skel.get_bone_pose_rotation(_skel.find_bone("forearm")).get_angle()
	_max_rot = maxf(_max_rot, maxf(ru, rf))

func _finish() -> void:
	if _max_rot < 0.2:
		_fails.append("IK did not rotate arm (max_rot=" + str(_max_rot) + ")")
	for f in _fails:
		print("FAIL ", f)
	print("TEST arm_solve=", _fails.is_empty(), " max_rot=", _max_rot)
	quit(0 if _fails.is_empty() else 1)
