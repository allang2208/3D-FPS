extends SceneTree
## 检查导入 Mesh 是否带顶点色
## 运行： $env:PROBE_MESH='res://assets/models/ak/akm_voxel.obj'; $godot --headless --path 'E:\3d\3-dfps' --script res://tests/probe_mesh_colors.gd

func _process(_delta: float) -> bool:
	var path := OS.get_environment("PROBE_MESH")
	if path == "":
		path = "res://assets/models/ak/akm_voxel.obj"
	var mesh := load(path) as Mesh
	print("loaded:", mesh != null, " type=", mesh.get_class() if mesh else "null")
	if mesh == null:
		quit(1)
		return false
	var am := mesh as ArrayMesh
	var arrays := am.surface_get_arrays(0)
	print("surfaces=", am.get_surface_count(), " verts=", (arrays[Mesh.ARRAY_VERTEX] as PackedVector3Array).size())
	var cols := arrays[Mesh.ARRAY_COLOR] as PackedColorArray
	if cols == null:
		print("NO vertex colors")
	else:
		print("vertex colors: ", cols.size())
		var minc := Color(1, 1, 1)
		var maxc := Color(0, 0, 0)
		for i in range(cols.size()):
			minc.r = minf(minc.r, cols[i].r)
			minc.g = minf(minc.g, cols[i].g)
			minc.b = minf(minc.b, cols[i].b)
			maxc.r = maxf(maxc.r, cols[i].r)
			maxc.g = maxf(maxc.g, cols[i].g)
			maxc.b = maxf(maxc.b, cols[i].b)
		print("color range: ", minc, " .. ", maxc)
	quit(0)
	return false
