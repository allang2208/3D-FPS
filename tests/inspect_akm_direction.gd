extends SceneTree
## 判定 AKM GLB 枪管朝向：按 X 轴两端 5% 切片的顶点半径分布
## 枪管端应细（半径小），枪托/机匣端应粗
## 运行：& $godot --headless --path 'E:\3d\3-dfps' --script res://tests/inspect_akm_direction.gd

func _process(_delta: float) -> bool:
	var glb: PackedScene = load("res://assets/models/akm_trellis.glb")
	var n := glb.instantiate()
	root.add_child(n)
	var mi := n.get_node("geometry_0") as MeshInstance3D
	var mesh := mi.mesh as ArrayMesh
	var arrays := mesh.surface_get_arrays(0)
	var verts: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
	var min_x := INF
	var max_x := -INF
	for v in verts:
		min_x = minf(min_x, v.x)
		max_x = maxf(max_x, v.x)
	var span := max_x - min_x
	var lo := 0.0
	var hi := 0.0
	for v in verts:
		var rel := (v.x - min_x) / span
		var r := Vector2(v.y, v.z).length()
		if rel < 0.1:
			lo += r
		elif rel > 0.9:
			hi += r
	var n_lo := 0
	var n_hi := 0
	for v in verts:
		var rel := (v.x - min_x) / span
		if rel < 0.1:
			n_lo += 1
		elif rel > 0.9:
			n_hi += 1
	print("X_range=", min_x, "..", max_x)
	print("end_low(-X): avg_r=", lo / maxf(n_lo, 1), " verts=", n_lo)
	print("end_high(+X): avg_r=", hi / maxf(n_hi, 1), " verts=", n_hi)
	# 细端 = 枪口
	if lo / maxf(n_lo, 1) < hi / maxf(n_hi, 1):
		print("MUZZLE at -X side")
	else:
		print("MUZZLE at +X side")
	quit(0)
	return false
