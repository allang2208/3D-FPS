extends Node3D
## 第一人称左臂视模（支持手）：程序化 3 节骨骼 + 蒙皮，Godot 4.7 IterateIK3D 驱动。
## - 骨骼：上臂(肩) → 前臂(肘) → 手(腕)，rest 关节坐标在枪节点本地空间（本节点挂在 Gun 下，恒等变换）
## - IK 目标 = 弹匣实时位置（gun._mag 的全局坐标转枪本地）：平时手搭在弹匣位，
##   换弹时手跟随弹匣下滑/插入（真·IK，非纯程序化偏移）
## - ADS 时隐藏（避免遮挡觇孔视线）；换弹时 gun.gd 强制关 ADS，手臂必然可见
## 挂载：由 gun.gd 自动 add_child（任何武器通用，目标始终取当前 _mag）

# 关节坐标（枪节点本地空间；枪本地原点=相机空间持枪位，+X 右 / +Y 上 / +Z 后）
# 关节坐标按"左手从画面左下伸向弹匣"布局：肩在左下、肘居中、腕落在弹匣握持点附近，
# 使程序化 IK 手臂在弹匣下滑 0.20 时仍够得到（旧坐标手骨距弹匣 0.75m，超出臂长→换弹断手）
const SHOULDER := Vector3(-0.40, -0.16, 0.14)
const ELBOW := Vector3(-0.22, -0.07, 0.08)
const WRIST := Vector3(-0.03, -0.055, 0.025)
const UPPER_RADIUS := 0.042
const FOREARM_RADIUS := 0.035
const HAND_EXTEND := 0.085     # 末端骨延长：指尖够到目标
const GRIP_OFFSET := Vector3(-0.03, -0.02, 0.015)  # 手抓弹匣的着点（相对弹匣中心，避开机匣）
const ARM_SEGMENTS := 10

var _skel: Skeleton3D
var _hand_target: Node3D
var _bone_idx := {}
var _vertex_count := 0

func _ready() -> void:
	name = "LeftArm"
	print("[arm] step skeleton")
	_build_skeleton()
	print("[arm] step mesh")
	_build_mesh()
	print("[arm] step ik")
	_build_ik()
	print("[arm] ready done")

func _process(_delta: float) -> void:
	var gun := get_parent()
	if gun == null or not is_instance_valid(gun):
		return
	var mag: Node3D = gun.get("_mag")
	var ads := 0.0
	var ads_raw = gun.get("_ads_factor")
	if ads_raw is float:
		ads = ads_raw
	# ADS 隐藏，避免遮挡觇孔
	visible = ads < 0.55
	if mag is Node3D and is_instance_valid(mag):
		_hand_target.position = gun.to_local(mag.global_position) + GRIP_OFFSET

func _build_skeleton() -> void:
	_skel = Skeleton3D.new()
	_skel.name = "ArmSkeleton"
	add_child(_skel)
	for bone_name in ["upper_arm", "forearm", "hand"]:
		_skel.add_bone(bone_name)
	var joints: Array[Vector3] = [SHOULDER, ELBOW, WRIST]
	var parents: Array[int] = [-1, 0, 1]
	for i in joints.size():
		var p: int = int(parents[i])
		_skel.set_bone_parent(i, p)
		if p < 0:
			_skel.set_bone_rest(i, Transform3D(Basis.IDENTITY, joints[i]))
		else:
			_skel.set_bone_rest(i, Transform3D(Basis.IDENTITY, joints[i] - joints[p]))
		_bone_idx[_skel.get_bone_name(i)] = i
	# Godot 4.7：全局姿态缓存默认是空的（get_bone_global_pose 恒为零），
	# 不重建缓存会导致 IK 解算器拿到的链坐标全为原点 → “The vectors must not be zero”。
	_skel.reset_bone_poses()
	_hand_target = Node3D.new()
	_hand_target.name = "HandTarget"
	_hand_target.position = GRIP_OFFSET
	add_child(_hand_target)

func _build_mesh() -> void:
	_vertex_count = 0
	var st_arm := SurfaceTool.new()
	st_arm.begin(Mesh.PRIMITIVE_TRIANGLES)
	_add_cylinder(st_arm, SHOULDER, ELBOW, UPPER_RADIUS, 0)
	_add_cylinder(st_arm, ELBOW, WRIST, FOREARM_RADIUS, 1)
	var mesh := st_arm.commit()
	var st_hand := SurfaceTool.new()
	st_hand.begin(Mesh.PRIMITIVE_TRIANGLES)
	_add_hand(st_hand)
	mesh = st_hand.commit(mesh)
	var skin := Skin.new()
	skin.set_bind_count(3)
	for i in 3:
		skin.set_bind_name(i, _skel.get_bone_name(i))
		# 关键：Skin 的 bind pose 存的是逆绑定矩阵（= global rest 的逆）。
		# 不取逆会导致顶点被变换两倍、全部甩出屏幕外（蒙皮手臂一直隐形）。
		skin.set_bind_pose(i, _skel.get_bone_global_rest(i).affine_inverse())
	var mi := MeshInstance3D.new()
	mi.name = "ArmMesh"
	mi.mesh = mesh
	mi.skin = skin
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(mi)
	mi.skeleton = mi.get_path_to(_skel)
	# 分段材质：衣袖（上臂/前臂）深灰战术服，手套（手）近黑
	var sleeve := StandardMaterial3D.new()
	sleeve.albedo_color = Color(0.17, 0.18, 0.21)
	sleeve.roughness = 0.9
	sleeve.metallic = 0.05
	mesh.surface_set_material(0, sleeve)
	var glove := StandardMaterial3D.new()
	glove.albedo_color = Color(0.19, 0.20, 0.23)
	glove.roughness = 0.75
	glove.metallic = 0.05
	mesh.surface_set_material(1, glove)

func _build_ik() -> void:
	var ik := JacobianIK3D.new()
	ik.name = "ReloadIK"
	_skel.add_child(ik)
	ik.set_setting_count(1)
	ik.set_root_bone_name(0, "upper_arm")
	ik.set_end_bone_name(0, "hand")
	ik.set_target_node(0, ik.get_path_to(_hand_target))
	# 关键：mutable_bone_axes=true 时求解器读 bone POSE 原点（我们没设，恒为零→链长 0→不解算）。
	# 关掉后读 bone REST，配合 reset_bone_poses() 缓存才能正常工作。
	ik.mutable_bone_axes = false
	ik.set_joint_rotation_axis(0, 0, SkeletonModifier3D.ROTATION_AXIS_ALL)
	ik.set_joint_rotation_axis(0, 1, SkeletonModifier3D.ROTATION_AXIS_ALL)
	ik.set_joint_rotation_axis(0, 2, SkeletonModifier3D.ROTATION_AXIS_ALL)
	ik.max_iterations = 16
	ik.min_distance = 0.002

## 圆管段（蒙皮权重 1.0 到指定骨）：沿 a→b，环分段，外向法线
func _add_cylinder(st: SurfaceTool, a: Vector3, b: Vector3, r: float, bone: int) -> void:
	var axis := (b - a).normalized()
	var basis := Basis.IDENTITY
	if absf(axis.dot(Vector3.UP)) < 0.9999:
		basis = Basis(Quaternion(Vector3.UP, axis))
	var len := a.distance_to(b)
	var base := _vertex_count
	for ring in 2:
		var y := 0.0 if ring == 0 else len
		for s in ARM_SEGMENTS:
			var ang := TAU * s / ARM_SEGMENTS
			var local := Vector3(cos(ang) * r, y, sin(ang) * r)
			var n := Vector3(cos(ang), 0.0, sin(ang))
			st.set_normal(basis * n)
			st.set_bones(PackedInt32Array([bone, 0, 0, 0]))
			st.set_weights(PackedFloat32Array([1.0, 0.0, 0.0, 0.0]))
			st.add_vertex(a + basis * local)
			_vertex_count += 1
	for s in ARM_SEGMENTS:
		var s2 := (s + 1) % ARM_SEGMENTS
		var i00 := base + s
		var i01 := base + s2
		var i10 := base + ARM_SEGMENTS + s
		var i11 := base + ARM_SEGMENTS + s2
		st.add_index(i00)
		st.add_index(i01)
		st.add_index(i10)
		st.add_index(i01)
		st.add_index(i11)
		st.add_index(i10)

## 拳头（全权重到手骨，沿骨 +Y 伸展）：圆柱拼接的握拳手型，绕序与手臂圆柱一致
func _add_hand(st: SurfaceTool) -> void:
	# 拳身：腕部上方 6cm 的圆拳
	_add_cylinder(st, WRIST + Vector3(0.002, 0.004, 0.0), WRIST + Vector3(0.002, 0.060, 0.0), 0.034, 2)
	# 拳峰：四指蜷起的隆起（略窄、略靠前）
	_add_cylinder(st, WRIST + Vector3(-0.003, 0.056, -0.003), WRIST + Vector3(-0.003, 0.076, -0.003), 0.028, 2)
	# 拇指：从拳身外侧斜向前上方伸出
	_add_cylinder(st, WRIST + Vector3(0.030, 0.018, 0.008), WRIST + Vector3(0.054, 0.034, 0.000), 0.014, 2)
