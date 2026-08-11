extends SceneTree
## 隔离探针：仅构建 LeftArm（无枪），开关 IK 定位 Quaternion 零向量来源

var _frames := 0
var _arm: Node3D
var _ik: JacobianIK3D

func _process(_delta: float) -> bool:
	_frames += 1
	if _frames == 1:
		_arm = Node3D.new()
		_arm.set_script(load("res://scripts/viewmodel_arms.gd"))
		root.add_child(_arm)
		print("arm added")
	if _frames == 2:
		print("frame2 ok, arm children=", _arm.get_child_count())
	if _frames == 3:
		_ik = _arm.get_node("ArmSkeleton/ReloadIK") as JacobianIK3D
		_ik.active = false
		print("ik disabled")
	if _frames == 5:
		_ik.active = true
		print("ik enabled")
	if _frames == 8:
		quit(0)
		return false
	return false
