class_name WolfRig
extends Node3D
## 黑狼程序化四足骨架：移植自 three.js 原型 fps3d/src/enemies.js
## 18 骨骼（脊柱5 + 尾1 + 四腿×3），逆平方距离自动蒙皮，正弦公式驱动步态/扑咬/死亡。
## GLB 蒙皮一次性成本高（23万顶点），故用 tools/bake_wolf_rig.gd 离线烘焙成
## assets/models/black_wolf_rigged.scn，运行时直接实例化；build_rigged() 仅供烘焙工具调用。
## 与旧版差异：旧版蒙皮线段→骨骼有错位（线段索引直接当骨骼索引），本版按“线段归属骨骼”修正；
## 旧版死亡摊腿 startsWith('R') 恒为 false，本版按左右腿正确取符号。

# [name, parent_name, 模型空间关节坐标]（2026-08-09 按 CuMesh 版新狼重新实测）
const BONE_DEFS := [
	["pelvis", "", Vector3(0.0, 0.136, -0.22)],
	["spineMid", "pelvis", Vector3(0.0, 0.138, -0.05)],
	["chest", "spineMid", Vector3(0.0, 0.124, 0.10)],
	["neck", "chest", Vector3(0.0, 0.160, 0.24)],
	["head", "neck", Vector3(0.0, 0.136, 0.40)],
	["tail", "pelvis", Vector3(0.0, 0.0, -0.35)],
	["FLRoot", "pelvis", Vector3(-0.082, -0.010, 0.177)],
	["FLKnee", "FLRoot", Vector3(-0.080, -0.12, 0.21)],
	["FLPaw", "FLKnee", Vector3(-0.078, -0.227, 0.240)],
	["FRRoot", "pelvis", Vector3(0.082, -0.005, 0.175)],
	["FRKnee", "FRRoot", Vector3(0.087, -0.11, 0.185)],
	["FRPaw", "FRKnee", Vector3(0.091, -0.227, 0.195)],
	["HLRoot", "pelvis", Vector3(-0.082, -0.012, -0.190)],
	["HLKnee", "HLRoot", Vector3(-0.094, -0.12, -0.21)],
	["HLPaw", "HLKnee", Vector3(-0.106, -0.226, -0.230)],
	["HRRoot", "pelvis", Vector3(0.082, -0.011, -0.184)],
	["HRKnee", "HRRoot", Vector3(0.095, -0.12, -0.21)],
	["HRPaw", "HRKnee", Vector3(0.107, -0.226, -0.233)],
]

# 蒙皮权重线段：[线段端点a, 线段端点b, 权重目标骨骼]（均为 BONE_DEFS 下标）
# 大腿段归 Root、小腿段归 Knee，脊柱段归下端骨，头/尾归自身
const SKIN_SEGS := [
	[0, 1, 0], # 骨盆→腰
	[1, 2, 1], # 腰→胸
	[2, 3, 2], # 胸→颈
	[3, 4, 4], # 颈→头
	[0, 5, 5], # 骨盆→尾
	[6, 7, 6], [7, 8, 7], # 前左 大腿/小腿
	[9, 10, 9], [10, 11, 10], # 前右
	[12, 13, 12], [13, 14, 13], # 后左
	[15, 16, 15], [16, 17, 16], # 后右
]

const LEG_PHASE := [0.0, PI, PI, 0.0] # FL FR HL HR，对角同相（trot）
const ATTACK_WINDOW := 0.25 # 对齐 enemy.gd 的 _lunge_t 时长
const MAX_INFLUENCES := 4

var _skel: Skeleton3D
var _bone_idx := {} # name -> int
var _legs := [] # [{name, root, knee}]


func _ready() -> void:
	_init_bone_map()


func _init_bone_map() -> bool:
	if _skel != null:
		return true
	for c in get_children():
		if c is Skeleton3D:
			_skel = c
			break
	if _skel == null:
		return false
	for i in _skel.get_bone_count():
		_bone_idx[_skel.get_bone_name(i)] = i
	for leg_name in ["FL", "FR", "HL", "HR"]:
		_legs.append({
			"name": leg_name,
			"root": _bone_idx[leg_name + "Root"],
			"knee": _bone_idx[leg_name + "Knee"],
		})
	return true


## 每帧驱动：t=步态时钟，moving=是否移动，attack_t=扑咬剩余时间（0 表示无），dead=死亡瘫软
func rig_update(t: float, moving: bool, attack_t: float, dead: bool) -> void:
	if _skel == null and not _init_bone_map():
		return
	var off := {} # bone_idx -> Vector3(rx, ry, rz) 欧拉偏移
	if dead:
		_acc(off, _bone_idx["spineMid"], 0.35)
		_acc(off, _bone_idx["chest"], 0.25)
		_acc(off, _bone_idx["neck"], 0.55)
		_acc(off, _bone_idx["head"], 0.45)
		for leg in _legs:
			var sgn := -1.0 if leg["name"][1] == "L" else 1.0
			_acc(off, leg["root"], 0.0, 0.0, sgn * 0.22)
			_acc(off, leg["knee"], 0.18)
	else:
		var amp := 1.0 if moving else 0.22
		for i in _legs.size():
			var leg: Dictionary = _legs[i]
			var sw := sin(t + LEG_PHASE[i])
			_acc(off, leg["root"], -sw * 0.5 * amp) # rotation.x 负 → 爪向前
			_acc(off, leg["knee"], maxf(0.0, sw) * 0.85 * amp * 0.8) # 摆动相才屈膝
		# 身体：移动前倾低头 + 左右摆动；待机呼吸
		_acc(off, _bone_idx["spineMid"], -0.06 * amp + sin(t) * 0.02 * amp, sin(t * 0.5) * 0.05 * amp)
		_acc(off, _bone_idx["chest"], sin(t + 0.7) * 0.02 * amp)
		_acc(off, _bone_idx["neck"], -0.08 * amp + sin(t * 0.5) * 0.025 * amp)
		_acc(off, _bone_idx["head"], -0.12 * amp + sin(t * 0.5 + 0.4) * 0.03 * amp, sin(t * 0.25) * 0.05 * amp)
		_acc(off, _bone_idx["tail"], sin(t * 0.5) * 0.22 * amp, sin(t * 0.25) * 0.16 * amp)
		# 攻击扑咬（attack_t 从 ATTACK_WINDOW 倒数到 0，脉冲中间最大）
		if attack_t > 0.0:
			var pulse := sin(minf(1.0, attack_t / ATTACK_WINDOW) * PI)
			_acc(off, _bone_idx["spineMid"], -0.18 * pulse)
			_acc(off, _bone_idx["neck"], 0.28 * pulse)
			_acc(off, _bone_idx["head"], 0.38 * pulse)
			for leg in _legs:
				if leg["name"][0] == "F":
					_acc(off, leg["root"], -0.3 * pulse)
					_acc(off, leg["knee"], 0.35 * pulse)
	for idx in off:
		_skel.set_bone_pose_rotation(idx, _euler_to_quat(off[idx]))


func rig_reset() -> void:
	if _skel == null and not _init_bone_map():
		return
	for i in _skel.get_bone_count():
		_skel.set_bone_pose_rotation(i, Quaternion.IDENTITY)


static func _acc(off: Dictionary, idx: int, rx: float, ry: float = 0.0, rz: float = 0.0) -> void:
	var e: Vector3 = off.get(idx, Vector3.ZERO)
	off[idx] = e + Vector3(rx, ry, rz)


## 与 three.js Euler 'XYZ' 一致：q = qx * qy * qz（绑定姿态为零旋转，偏移即绝对姿态）
static func _euler_to_quat(e: Vector3) -> Quaternion:
	return Quaternion(Vector3(1, 0, 0), e.x) * Quaternion(Vector3(0, 1, 0), e.y) * Quaternion(Vector3(0, 0, 1), e.z)


## 从 GLB 实例构建带骨架/蒙皮的黑狼（一次性高成本，仅烘焙工具调用）。
## 顶点烘到 GLB 根空间，骨骼静止姿态与 BONE_DEFS 坐标同空间。
## ext_weights 非空时使用外部权重（[PackedInt32Array, PackedFloat32Array]，每顶点4影响），
## 例如 UniRig 权重转移产物（tools/bake_wolf_rig.gd 的 WEIGHTS_BIN）；为空则用距离权重现算。
static func build_rigged(src: Node3D, ext_weights: Array = []) -> WolfRig:
	var rig := WolfRig.new()
	rig.name = src.name
	var skel := Skeleton3D.new()
	skel.name = "Skeleton3D"
	rig.add_child(skel)
	for i in BONE_DEFS.size():
		skel.add_bone(BONE_DEFS[i][0])
	for i in BONE_DEFS.size():
		var parent_name: String = BONE_DEFS[i][1]
		var world: Vector3 = BONE_DEFS[i][2]
		if parent_name == "":
			skel.set_bone_rest(i, Transform3D(Basis.IDENTITY, world))
		else:
			var p := _bone_index_of(parent_name)
			skel.set_bone_parent(i, p)
			skel.set_bone_rest(i, Transform3D(Basis.IDENTITY, world - BONE_DEFS[p][2]))
	skel.owner = rig

	var skin := Skin.new()
	skin.set_bind_count(BONE_DEFS.size())
	for i in BONE_DEFS.size():
		skin.set_bind_name(i, skel.get_bone_name(i))
		skin.set_bind_pose(i, skel.get_bone_global_rest(i))

	var seg_data := []
	for s in SKIN_SEGS:
		seg_data.append([BONE_DEFS[s[0]][2], BONE_DEFS[s[1]][2], s[2]])

	var mis := []
	_collect_mesh_instances(src, mis)
	for mi: MeshInstance3D in mis:
		var rel := _relative_transform(src, mi)
		var out := ArrayMesh.new()
		for si in mi.mesh.get_surface_count():
			var arrays: Array = mi.mesh.surface_get_arrays(si)
			var verts: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX].duplicate()
			for vi in verts.size():
				verts[vi] = rel * verts[vi]
			arrays[Mesh.ARRAY_VERTEX] = verts
			if arrays[Mesh.ARRAY_NORMAL] != null:
				var norms: PackedVector3Array = arrays[Mesh.ARRAY_NORMAL].duplicate()
				for ni in norms.size():
					norms[ni] = (rel.basis * norms[ni]).normalized()
				arrays[Mesh.ARRAY_NORMAL] = norms
			var bw: Array
			if ext_weights.is_empty():
				bw = _compute_weights(verts, seg_data)
			else:
				if (ext_weights[0] as PackedInt32Array).size() != verts.size() * MAX_INFLUENCES:
					push_error("外部权重顶点数不匹配: weights=%d verts*4=%d" % [(ext_weights[0] as PackedInt32Array).size(), verts.size() * MAX_INFLUENCES])
					return null
				bw = ext_weights
			arrays[Mesh.ARRAY_BONES] = bw[0]
			arrays[Mesh.ARRAY_WEIGHTS] = bw[1]
			out.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
			var mat: Material = mi.mesh.surface_get_material(si)
			if mat == null:
				mat = mi.get_active_material(si)
			out.surface_set_material(si, mat)
		var out_mi := MeshInstance3D.new()
		out_mi.name = mi.name
		out_mi.mesh = out
		out_mi.skin = skin
		rig.add_child(out_mi)
		out_mi.owner = rig
		out_mi.skeleton = out_mi.get_path_to(skel)
	return rig


static func _bone_index_of(bone_name: String) -> int:
	for i in BONE_DEFS.size():
		if BONE_DEFS[i][0] == bone_name:
			return i
	return -1


static func _collect_mesh_instances(n: Node, out: Array) -> void:
	if n is MeshInstance3D and n.mesh != null:
		out.append(n)
	for c in n.get_children():
		_collect_mesh_instances(c, out)


static func _relative_transform(root: Node3D, node: Node3D) -> Transform3D:
	var t := Transform3D.IDENTITY
	var cur: Node = node
	while cur != null and cur != root:
		if cur is Node3D:
			t = cur.transform * t
		cur = cur.get_parent()
	return t


## 顶点到骨骼线段的逆平方距离权重，取 top-4 归一化（移植 computeSkinWeights）
## 内层循环全部摊平为标量运算（GDScript 的 Vector3/Variant 开销在 23万顶点×13线段 下不可接受）
static func _compute_weights(verts: PackedVector3Array, segs: Array) -> Array:
	var n := verts.size()
	var bones := PackedInt32Array()
	var weights := PackedFloat32Array()
	bones.resize(n * MAX_INFLUENCES)
	weights.resize(n * MAX_INFLUENCES)
	const EPS := 0.0005
	var seg_count: int = segs.size()
	var ax := PackedFloat32Array()
	var ay := PackedFloat32Array()
	var az := PackedFloat32Array()
	var bx := PackedFloat32Array()
	var by := PackedFloat32Array()
	var bz := PackedFloat32Array()
	var sl2 := PackedFloat32Array()
	var target := PackedInt32Array()
	for s in segs:
		var a: Vector3 = s[0]
		var b: Vector3 = s[1]
		ax.append(a.x)
		ay.append(a.y)
		az.append(a.z)
		var ab := b - a
		bx.append(ab.x)
		by.append(ab.y)
		bz.append(ab.z)
		sl2.append(ab.length_squared())
		target.append(s[2])
	var t_last := Time.get_ticks_msec()
	for vi in n:
		var p := verts[vi]
		var px := p.x
		var py := p.y
		var pz := p.z
		var w0 := -1.0
		var w1 := -1.0
		var w2 := -1.0
		var w3 := -1.0
		var i0 := 0
		var i1 := 0
		var i2 := 0
		var i3 := 0
		for si in seg_count:
			var apx := px - ax[si]
			var apy := py - ay[si]
			var apz := pz - az[si]
			var l2: float = sl2[si]
			var t: float = clampf((apx * bx[si] + apy * by[si] + apz * bz[si]) / l2, 0.0, 1.0) if l2 > 1e-12 else 0.0
			var qx := apx - bx[si] * t
			var qy := apy - by[si] * t
			var qz := apz - bz[si] * t
			var w: float = 1.0 / (qx * qx + qy * qy + qz * qz + EPS)
			if w > w0:
				w3 = w2; i3 = i2
				w2 = w1; i2 = i1
				w1 = w0; i1 = i0
				w0 = w; i0 = target[si]
			elif w > w1:
				w3 = w2; i3 = i2
				w2 = w1; i2 = i1
				w1 = w; i1 = target[si]
			elif w > w2:
				w3 = w2; i3 = i2
				w2 = w; i2 = target[si]
			elif w > w3:
				w3 = w; i3 = target[si]
		var sum: float = maxf(0.0, w0) + maxf(0.0, w1) + maxf(0.0, w2) + maxf(0.0, w3)
		var base := vi * MAX_INFLUENCES
		bones[base] = i0
		bones[base + 1] = i1
		bones[base + 2] = i2
		bones[base + 3] = i3
		if sum > 0.0:
			weights[base] = maxf(0.0, w0) / sum
			weights[base + 1] = maxf(0.0, w1) / sum
			weights[base + 2] = maxf(0.0, w2) / sum
			weights[base + 3] = maxf(0.0, w3) / sum
		else:
			weights[base] = 1.0
		if vi % 32768 == 0:
			var now := Time.get_ticks_msec()
			print("BAKE weights ", vi, "/", n, " (+", now - t_last, "ms)")
			t_last = now
	return [bones, weights]
