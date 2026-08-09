extends SceneTree
## 黑狼骨架烘焙：GLB 网格 → 18 骨骼 + 蒙皮 → .scn（一次性，离线运行）
## 运行：& $godot --headless --path 'E:\3d\3-dfps' --script res://tools/bake_wolf_rig.gd
##
## 权重两档（自动选择）：
## - WEIGHTS_BIN 存在 → 用 UniRig 权重转移产物（scripts/../tools/ai 管线生成，
##   源网格必须是 UniRig 版 GLB，顶点序与 bin 一致）；
## - 不存在 → 退回逆平方距离权重现算（任何静态 GLB 都能用，效果较差）。

const SRC_GLB := "res://assets/models/black_wolf_unirig.glb"
const WEIGHTS_BIN := "res://assets/models/black_wolf_unirig_weights.bin"
const OUT_SCN := "res://assets/models/black_wolf_rigged.scn"

var _ok := false

func _initialize() -> void:
	var t0 := Time.get_ticks_msec()
	var glb: PackedScene = load(SRC_GLB)
	if glb == null:
		push_error("GLB 加载失败: " + SRC_GLB)
		quit(1)
		return
	var ext_weights := _load_weights_bin(WEIGHTS_BIN)
	print("BAKE weights_src=", "unirig_bin" if not ext_weights.is_empty() else "distance_fallback")
	var src: Node3D = glb.instantiate()
	var rig: Node3D = WolfRig.build_rigged(src, ext_weights)
	src.free()
	if rig == null:
		push_error("build_rigged 失败")
		quit(1)
		return
	print("BAKE build_ms=", Time.get_ticks_msec() - t0)
	var packed := PackedScene.new()
	var err := packed.pack(rig)
	if err != OK:
		push_error("pack 失败: %s" % err)
		quit(1)
		return
	err = ResourceSaver.save(packed, OUT_SCN)
	if err != OK:
		push_error("保存失败: %s" % err)
		quit(1)
		return
	var verts := 0
	for c in rig.get_children():
		if c is MeshInstance3D:
			for si in c.mesh.get_surface_count():
				verts += (c.mesh.surface_get_arrays(si)[Mesh.ARRAY_VERTEX] as PackedVector3Array).size()
	print("BAKE ok bones=", WolfRig.BONE_DEFS.size(), " verts=", verts, " out=", OUT_SCN)
	rig.free()
	_ok = true
	quit(0)


## 读取权重 bin：[u32 顶点数][u32 每顶点影响数] + int32 bones[n*k] + float32 weights[n*k]
func _load_weights_bin(path: String) -> Array:
	if not FileAccess.file_exists(path):
		return []
	var f := FileAccess.open(path, FileAccess.READ)
	var n := f.get_32()
	var k := f.get_32()
	var bones := PackedInt32Array()
	bones.resize(n * k)
	var weights := PackedFloat32Array()
	weights.resize(n * k)
	for i in n * k:
		bones[i] = f.get_32()
	for i in n * k:
		weights[i] = f.get_float()
	print("BAKE bin loaded: verts=", n, " k=", k)
	return [bones, weights]


func _process(_delta: float) -> bool:
	# 正常流程在 _initialize 里同步跑完并 quit（quit 后可能再执行一帧，用 _ok 区分）；
	# _initialize 中途出错没走到 quit 时，兜底退出避免无头空转
	if _ok:
		return false
	push_error("bake 未正常结束（_initialize 未调用 quit）")
	quit(1)
	return true
