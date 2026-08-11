extends SceneTree
## 分析 lowpoly AKM 的瞄具候选：按枪轴 t 分箱打印最高点，定位真实觇孔/准星
## 运行：$godot --headless --path 'E:\3d\3-dfps' --script res://tests/probe_lowpoly_sights.gd

func _init() -> void:
	var body: Mesh = load("res://assets/models/ak/lowpoly_akm/lowpoly_body.tres")
	if body == null:
		print("LOAD FAIL")
		quit(1)
		return
	var verts := PackedVector3Array()
	for s in body.get_surface_count():
		var arr := body.surface_get_arrays(s)
		verts.append_array(arr[Mesh.ARRAY_VERTEX])
	var mn := INF
	var mx := -INF
	for v in verts:
		mn = minf(mn, v.z)
		mx = maxf(mx, v.z)
	var extent := mx - mn
	var center := body.get_aabb().get_center()
	print("verts=", verts.size(), " zmin=", mn, " zmax=", mx, " extent=", extent, " center=", center)
	# 与 gun.gd 一致：顶点先按 AABB 中心居中，t 以 +Z 为枪口端
	# 细化扫描 t 0.86-1.00（准星/枪口区）
	for i in 14:
		var t0 := 0.86 + i * 0.01
		var t1 := t0 + 0.01
		var best := -INF
		var best_v := Vector3.ZERO
		for v in verts:
			var vz: Vector3 = v - center
			var t := (vz.z - (mn - center.z)) / extent
			if t >= t0 and t < t1 and vz.y > best:
				best = vz.y
				best_v = vz
		if best > -100.0:
			print("t[", t0, "-", t1, "] top_y=", best, " at=", best_v)
	quit(0)
