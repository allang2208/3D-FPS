extends SceneTree
## 黑狼骨架烘焙：GLB 静态网格 → 自动蒙皮 → 带 Skeleton3D 的 .scn（一次性，离线运行）
## 运行：& $godot --headless --path 'E:\3d\3-dfps' --script res://tools/bake_wolf_rig.gd
## GLB 更新后重跑一次即可。

const SRC_GLB := "res://assets/models/black_wolf_trellis.glb"
const OUT_SCN := "res://assets/models/black_wolf_rigged.scn"

func _initialize() -> void:
	var t0 := Time.get_ticks_msec()
	var glb: PackedScene = load(SRC_GLB)
	if glb == null:
		push_error("GLB 加载失败: " + SRC_GLB)
		quit(1)
		return
	var src: Node3D = glb.instantiate()
	var rig: Node3D = WolfRig.build_rigged(src)
	src.free()
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


var _ok := false

func _process(_delta: float) -> bool:
	# 正常流程在 _initialize 里同步跑完并 quit（quit 后可能再执行一帧，用 _ok 区分）；
	# _initialize 中途出错没走到 quit 时，兜底退出避免无头空转
	if _ok:
		return false
	push_error("bake 未正常结束（_initialize 未调用 quit）")
	quit(1)
	return true
