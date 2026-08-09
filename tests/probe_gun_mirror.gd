extends SceneTree
## 镜像检测：AK 抛壳口在机匣右侧（面对枪口方向）。检查机匣区顶部
## z 不对称性 → 判断模型是否被左右镜像
## 运行： $env:PROBE_GLB='res://assets/models/xxx.glb'; $godot --headless --path 'E:\3d\3-dfps' --script res://tests/probe_gun_mirror.gd

func _process(_delta: float) -> bool:
	var path := OS.get_environment("PROBE_GLB")
	if path == "":
		path = "res://assets/models/ak/_dl_ak47_adamkokrito.glb"
	var glb: PackedScene = load(path)
	var n := glb.instantiate()
	root.add_child(n)
	var verts := PackedVector3Array()
	_collect(n, Transform3D(), verts)
	print("=== ", path, " verts=", verts.size())
	var mn := Vector3(INF, INF, INF)
	var mx := Vector3(-INF, -INF, -INF)
	for v in verts:
		mn = mn.min(v)
		mx = mx.max(v)
	print("aabb=", mn, "..", mx)
	# 机匣顶带（顶部 ~25%）：z 侧分布
	var top_lo := mn.y + (mx.y - mn.y) * 0.72
	var n_neg := 0
	var n_pos := 0
	var zneg_min := INF
	var zpos_max := -INF
	for v in verts:
		if v.y > top_lo:
			if v.z < -0.001:
				n_neg += 1
				zneg_min = minf(zneg_min, v.z)
			elif v.z > 0.001:
				n_pos += 1
				zpos_max = maxf(zpos_max, v.z)
	print("top band: z<0 verts=", n_neg, " (min ", zneg_min, ") | z>0 verts=", n_pos, " (max ", zpos_max, ")")
	# 机匣侧壁：y 在中部，看两侧 z 极端值
	var mid_lo := mn.y + (mx.y - mn.y) * 0.35
	var mid_hi := mn.y + (mx.y - mn.y) * 0.70
	var zmin := INF
	var zmax := -INF
	for v in verts:
		if v.y >= mid_lo and v.y <= mid_hi:
			zmin = minf(zmin, v.z)
			zmax = maxf(zmax, v.z)
	print("mid side: zmin=", zmin, " zmax=", zmax, " -> 抛壳口侧应在右侧")
	quit(0)
	return false

func _collect(node: Node, parent: Transform3D, out: PackedVector3Array) -> void:
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
		_collect(c, t, out)
