extends SceneTree
## 黑狼骨架冒烟：烘焙场景结构（18骨骼/蒙皮数组/权重归一）+ 步态/扑咬/死亡姿态驱动
## 运行：& $godot --headless --path 'E:\3d\3-dfps' --script res://tests/test_wolf_rig.gd
## 前置：先跑 res://tools/bake_wolf_rig.gd 生成 assets/models/black_wolf_rigged.scn

var _fails := 0

func _initialize() -> void:
	var packed: PackedScene = load("res://assets/models/black_wolf_rigged.scn")
	_check("scn_loaded", packed != null)
	if packed == null:
		_finish()
		return
	var rig: Node3D = packed.instantiate()
	root.add_child(rig)
	_check("is_wolfrig", rig is WolfRig)

	var skel: Skeleton3D = null
	var mi: MeshInstance3D = null
	for c in rig.get_children():
		if c is Skeleton3D:
			skel = c
		if c is MeshInstance3D:
			mi = c
	_check("skeleton_found", skel != null)
	_check("bone_count_18", skel != null and skel.get_bone_count() == 18)
	_check("mesh_found", mi != null and mi.mesh != null)
	if skel == null or mi == null:
		_finish()
		return

	# 骨骼层级：pelvis 是根，head 的父链到 pelvis
	_check("pelvis_is_root", skel.get_bone_parent(0) == -1)
	var head := skel.find_bone("head")
	_check("head_chain", skel.get_bone_parent(head) == skel.find_bone("neck"))

	# 蒙皮：骨骼/权重数组存在、每顶点 4 影响、权重归一
	var arrays := mi.mesh.surface_get_arrays(0)
	var bones: PackedInt32Array = arrays[Mesh.ARRAY_BONES]
	var weights: PackedFloat32Array = arrays[Mesh.ARRAY_WEIGHTS]
	var verts: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
	_check("skin_arrays", bones.size() == verts.size() * 4 and weights.size() == verts.size() * 4)
	var norm_ok := true
	var n := verts.size()
	for vi in [0, n / 16, n / 4, n / 2, n - 1]:
		var sum := 0.0
		for k in 4:
			sum += weights[vi * 4 + k]
		if absf(sum - 1.0) > 0.01:
			norm_ok = false
	_check("weights_normalized", norm_ok)
	_check("skeleton_path", mi.get_node_or_null(mi.skeleton) == skel)
	_check("skin_binds", mi.skin != null and mi.skin.get_bind_count() == 18)

	# 步态：t=0 时 FL/HR 处于中立、FR/HL 同相（对角 trot，phase=[0,π,π,0]）；
	# t=π/2 时 FL 摆动相（前摆+屈膝），FR 处于支撑相
	rig.rig_update(0.0, true, 0.0, false)
	var fl_root := skel.find_bone("FLRoot")
	var fr_knee := skel.find_bone("FRKnee")
	var fl_knee := skel.find_bone("FLKnee")
	var q0: Quaternion = skel.get_bone_pose_rotation(fl_root)
	_check("gait_t0_flroot_neutral", q0.angle_to(Quaternion.IDENTITY) < 0.01)
	_check("gait_t0_knees_straight", skel.get_bone_pose_rotation(fr_knee).angle_to(Quaternion.IDENTITY) < 0.01
		and skel.get_bone_pose_rotation(fl_knee).angle_to(Quaternion.IDENTITY) < 0.01)
	rig.rig_update(PI / 2, true, 0.0, false)
	var q1: Quaternion = skel.get_bone_pose_rotation(fl_root)
	_check("gait_swing_moves", q0.angle_to(q1) > 0.3)
	_check("gait_swing_knee_bent", skel.get_bone_pose_rotation(fl_knee).angle_to(Quaternion.IDENTITY) > 0.3)

	# 待机幅度衰减：同相位 moving=false 摆幅应明显小于 moving=true
	rig.rig_update(PI / 2, false, 0.0, false)
	var idle_ang: float = skel.get_bone_pose_rotation(fl_root).angle_to(Quaternion.IDENTITY)
	rig.rig_update(PI / 2, true, 0.0, false)
	var move_ang: float = skel.get_bone_pose_rotation(fl_root).angle_to(Quaternion.IDENTITY)
	_check("idle_amp_smaller", idle_ang < move_ang * 0.5)

	# 扑咬：attack_t 中段脉冲让头骨前倾
	rig.rig_update(0.0, false, 0.0, false)
	var head_neutral: Quaternion = skel.get_bone_pose_rotation(skel.find_bone("head"))
	rig.rig_update(0.0, false, 0.125, false)
	var head_attack: Quaternion = skel.get_bone_pose_rotation(skel.find_bone("head"))
	_check("attack_head_pitch", head_neutral.angle_to(head_attack) > 0.2)

	# 死亡：脊柱瘫软弯折 + 复位
	rig.rig_update(1.0, false, 0.0, true)
	var spine_dead := skel.get_bone_pose_rotation(skel.find_bone("spineMid")).angle_to(Quaternion.IDENTITY)
	_check("dead_spine_bend", absf(spine_dead - 0.35) < 0.05)
	rig.rig_reset()
	_check("reset_to_bind", skel.get_bone_pose_rotation(skel.find_bone("spineMid")).angle_to(Quaternion.IDENTITY) < 0.001)

	# 姿态沿骨骼链传播：FLRoot 摆动后 FLPaw 的 FK 全局位置位移 > 1cm
	# （无头模式 Skeleton3D 全局姿态缓存不刷新，故用 _fk_global 手工验算层级+姿态）
	rig.rig_update(0.0, true, 0.0, false)
	var paw := skel.find_bone("FLPaw")
	var p0: Vector3 = _fk_global(skel, paw).origin
	rig.rig_update(PI / 2, true, 0.0, false)
	var p1: Vector3 = _fk_global(skel, paw).origin
	_check("paw_moves", p0.distance_to(p1) > 0.01)

	_finish()

## 手工 FK：global = parent_global * rest * pose
func _fk_global(skel: Skeleton3D, idx: int) -> Transform3D:
	var local := skel.get_bone_rest(idx) * Transform3D(Basis(skel.get_bone_pose_rotation(idx)), Vector3.ZERO)
	var p := skel.get_bone_parent(idx)
	if p == -1:
		return local
	return _fk_global(skel, p) * local

func _check(label: String, ok: bool) -> void:
	if not ok:
		_fails += 1
	print("TEST ", label, "=", ok)

func _finish() -> void:
	print("TEST wolf_rig_fails=", _fails)
	quit(1 if _fails > 0 else 0)
