extends SceneTree
## 探测混元3D 生成的 AK GLB：顶点数、包围盒、瞄具顶部轮廓（与 TRELLIS 版对比）
## 运行： $godot --headless --path 'E:\3d\3-dfps' --script res://tests/probe_hy3d_ak.gd

func _process(_delta: float) -> bool:
	var path := OS.get_environment("HY3D_GLB")
	if path == "":
		path = "res://assets/models/ak/hunyuan/e826d5b7-3474-48a4-9ce4-228aa8691a6a_0.glb"
	var glb: PackedScene = load(path)
	print("probe file=", path)
	var n := glb.instantiate()
	root.add_child(n)
	_dump(n, 0)
	var all_verts := PackedVector3Array()
	_collect_verts(n, Transform3D(), all_verts)
	print("total_verts=", all_verts.size())
	var verts := all_verts
	var mn := Vector3(INF, INF, INF)
	var mx := Vector3(-INF, -INF, -INF)
	for v in verts:
		mn = mn.min(v)
		mx = mx.max(v)
	print("aabb=", mn, "..", mx, " size=", mx - mn)
	# 顶部轮廓：沿 X 切片
	var bins := 140
	var x0 := -0.55
	var dx := 1.1 / bins
	var tops: Array[float] = []
	tops.resize(bins)
	tops.fill(0.0)
	for v in verts:
		var i := int((v.x - x0) / dx)
		if i >= 0 and i < bins:
			tops[i] = maxf(tops[i], v.y)
	for i in range(bins):
		if tops[i] <= 0.0:
			tops[i] = -INF
	var sorted_tops := tops.duplicate()
	sorted_tops.sort()
	var valid: Array[float] = []
	for t in tops:
		if t > -INF:
			valid.append(t)
	valid.sort()
	print("median_top=", valid[valid.size() / 2])
	# 找凸起特征（高于中位数 0.01）
	var base: float = valid[valid.size() / 2]
	for i in range(bins):
		if tops[i] > base + 0.010:
			print("  bump x=", snappedf(x0 + (i + 0.5) * dx, 0.005), " top=", snappedf(tops[i], 0.002))
	quit(0)
	return false

func _collect_verts(node: Node, parent: Transform3D, out: PackedVector3Array) -> void:
	var t := parent
	if node is Node3D:
		t = parent * (node as Node3D).transform
	if node is MeshInstance3D:
		var mi := node as MeshInstance3D
		var mesh := mi.mesh as ArrayMesh
		if mesh:
			for s in range(mesh.get_surface_count()):
				var arrays := mesh.surface_get_arrays(s)
				if arrays.is_empty():
					continue
				var v: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
				for p in v:
					out.append(t * p)
	for c in node.get_children():
		_collect_verts(c, t, out)

func _dump(node: Node, depth: int) -> void:
	var pad := "  ".repeat(depth)
	var extra := ""
	if node is Node3D:
		extra = " pos=" + str((node as Node3D).position) + " rot=" + str((node as Node3D).rotation_degrees) + " scale=" + str((node as Node3D).scale)
	print(pad, node.get_class(), " ", node.name, extra)
	for c in node.get_children():
		_dump(c, depth + 1)
