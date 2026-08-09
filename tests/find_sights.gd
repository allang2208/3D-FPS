extends SceneTree
## 从 AKM GLB 网格自动定位瞄具：沿枪管轴(X)扫描顶部轮廓，
## 找相对基线的凸起（后照门/前照门），输出坐标供 ADS 校准
## 运行：& $godot --headless --path 'E:\3d\3-dfps' --script res://tests/find_sights.gd

func _process(_delta: float) -> bool:
	var glb: PackedScene = load("res://assets/models/akm_trellis.glb")
	var n := glb.instantiate()
	root.add_child(n)
	var mi := n.get_node("geometry_0") as MeshInstance3D
	var mesh := mi.mesh as ArrayMesh
	var arrays := mesh.surface_get_arrays(0)
	var verts: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
	# 沿 X 分段统计顶部高度
	var bins := 100
	var x0 := -0.5
	var dx := 1.0 / bins
	var tops: Array[float] = []
	tops.resize(bins)
	tops.fill(0.0)
	for v in verts:
		var i := int((v.x - x0) / dx)
		if i >= 0 and i < bins:
			tops[i] = maxf(tops[i], v.y)
	# 基线：取中位数高度（接收机顶部）
	var sorted_tops := tops.duplicate()
	sorted_tops.sort()
	var base: float = sorted_tops[bins / 2]
	print("base_top=", base)
	# 找所有明显凸起（高于基线 0.01）
	var bumps: Array[Vector2] = []
	for i in range(bins):
		if tops[i] > base + 0.010:
			bumps.append(Vector2(x0 + (i + 0.5) * dx, tops[i]))
	# 聚类：把相邻凸起合并成特征
	var features: Array[Dictionary] = []
	for b in bumps:
		if features.is_empty() or b.x - float(features[-1]["x_end"]) > 0.02:
			features.append({"x_start": b.x, "x_end": b.x, "h_max": b.y, "h_at": b.x})
		else:
			features[-1]["x_end"] = b.x
			if b.y > float(features[-1]["h_max"]):
				features[-1]["h_max"] = b.y
				features[-1]["h_at"] = b.x
	print("features (x_start, x_end, h_max, at_x):")
	for f in features:
		print("  x=", f["x_start"], "..", f["x_end"], " h=", f["h_max"], " at=", f["h_at"])
	# 前段（枪管区 x>0.15）精细扫描：每 0.005 一段，找高于局部基线的凸起
	print("--- front section scan (x>0.15) ---")
	var fx0 := 0.15
	var fdx := 0.005
	var ftops: Array[float] = []
	ftops.resize(70)
	ftops.fill(0.0)
	for v in verts:
		if v.x < fx0:
			continue
		var i := int((v.x - fx0) / fdx)
		if i >= 0 and i < ftops.size():
			ftops[i] = maxf(ftops[i], v.y)
	# 局部基线：中位数
	var fsorted := ftops.duplicate()
	fsorted.sort()
	var fbase: float = fsorted[fsorted.size() / 2]
	print("front_base=", fbase)
	for i in range(ftops.size()):
		if ftops[i] > fbase + 0.006:
			print("  x=", fx0 + i * fdx, " top=", ftops[i])
	# 完整枪管段 0.15..0.5 每 0.01：顶部 + 顶部 z 宽度
	print("--- full front profile ---")
	for i in range(35):
		var xa := 0.15 + i * 0.01
		var xb := xa + 0.01
		var top_y := 0.0
		var top_zs: Array[float] = []
		for v in verts:
			if v.x >= xa and v.x < xb:
				if v.y > top_y - 0.001:
					if absf(v.y - top_y) < 0.001:
						top_zs.append(v.z)
					else:
						top_y = v.y
						top_zs = [v.z]
		if top_zs.size() > 0:
			var zmin := INF
			var zmax := -INF
			for z in top_zs:
				zmin = minf(zmin, z)
				zmax = maxf(zmax, z)
			print("  x=", xa, " top_y=", top_y, " top_z_w=", zmax - zmin)
	# 接收机顶部基线：x in [-0.4, 0.1] 顶部高度的直方图
	print("--- receiver top histogram (x -0.4..0.1) ---")
	var hist: Dictionary = {}
	for v in verts:
		if v.x >= -0.4 and v.x <= 0.1:
			var key := snappedf(v.y, 0.005)
			hist[key] = int(hist.get(key, 0)) + 1
	var items: Array = []
	for k in hist:
		items.append([k, hist[k]])
	items.sort_custom(func(a, b): return a[1] > b[1])
	for it in items.slice(0, 12):
		print("  y=", it[0], " count=", it[1])
	quit(0)
	return false
