extends SceneTree
## 枪口方向判定探测器：对给定 GLB，量化两端粗细/顶部轮廓/瞄具位置，
## 判断哪端是枪口（细端+前准星+枪管），哪端是枪托
## 运行： $env:PROBE_GLB='res://assets/models/xxx.glb'; $godot --headless --path 'E:\3d\3-dfps' --script res://tests/probe_gun_direction.gd

func _process(_delta: float) -> bool:
	var path := OS.get_environment("PROBE_GLB")
	if path == "":
		path = "res://assets/models/akm_hunyuan_lowpoly.glb"
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
	print("aabb=", mn, "..", mx, " len=", (mx - mn).x)
	var axis := 0
	var extent := mx.x - mn.x
	# 两端粗细
	_analyze_end(verts, axis, mn, extent, 0.06)
	# 顶部轮廓（细扫描 + z 宽）
	var bins := 190
	var tops := PackedFloat32Array()
	tops.resize(bins)
	tops.fill(-INF)
	var zmin_at := PackedFloat32Array()
	zmin_at.resize(bins)
	zmin_at.fill(INF)
	var zmax_at := PackedFloat32Array()
	zmax_at.resize(bins)
	zmax_at.fill(-INF)
	for v in verts:
		var i := clampi(int((v.x - mn.x) / extent * bins), 0, bins - 1)
		if v.y > tops[i]:
			tops[i] = v.y
	for v in verts:
		var i := clampi(int((v.x - mn.x) / extent * bins), 0, bins - 1)
		if v.y > tops[i] - 0.004:
			zmin_at[i] = minf(zmin_at[i], v.z)
			zmax_at[i] = maxf(zmax_at[i], v.z)
	print("--- top profile (x, top_y, top_z_width) 每 2 bin ---")
	for i in range(0, bins, 2):
		if tops[i] > -INF:
			print("  x=", snappedf(mn.x + (i + 0.5) * extent / bins, 0.01),
				" top=", snappedf(tops[i], 0.002),
				" zw=", snappedf(zmax_at[i] - zmin_at[i], 0.005))
	quit(0)
	return false

func _analyze_end(verts: PackedVector3Array, axis: int, mn: Vector3, extent: float, frac: float) -> void:
	for end_name in ["-X(端1)", "+X(端2)"]:
		var sum := Vector3.ZERO
		var rsum := 0.0
		var cnt := 0
		var top_y := 0.0
		for v in verts:
			var rel := (v[axis] - mn[axis]) / extent
			if (end_name.begins_with("-") and rel < frac) or (end_name.begins_with("+") and rel > 1.0 - frac):
				sum += v
				rsum += Vector2(v.y, v.z).length()
				cnt += 1
				top_y = maxf(top_y, v.y)
		if cnt > 0:
			var c := sum / cnt
			print("  end", end_name, " avg_r=", snappedf(rsum / cnt, 0.003),
				" centroid=(", snappedf(c.x, 0.003), ",", snappedf(c.y, 0.003), ",", snappedf(c.z, 0.003), ")",
				" top_y=", snappedf(top_y, 0.003))

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
