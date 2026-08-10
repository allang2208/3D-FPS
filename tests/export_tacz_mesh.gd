extends SceneTree
## 把 TACZ GLB 的网格转成静态 ArrayMesh .tres（绕开骨骼蒙皮，走 AKM 已验证管线）。
## GLB 的 bind pose = identity，顶点即模型原始坐标（归一化+居中后）；去掉骨骼权重即可静态使用。
## 用法：
##   $env:TACZ_BODY='res://assets/models/tacz_ak47/ak47_v3.glb'
##   $env:TACZ_MAG='res://assets/models/tacz_ak47/ak47_mag_v3.glb'
##   $env:TACZ_TEX='res://assets/models/tacz_ak47/ak47.png'
##   $env:TACZ_BODY_OUT='res://assets/models/tacz_ak47/ak47_body.tres'
##   $env:TACZ_MAG_OUT='res://assets/models/tacz_ak47/ak47_mag.tres'
##   $godot --headless --path 'E:\3d\3-dfps' --script res://tests/export_tacz_mesh.gd

func _init() -> void:
	var body_src := OS.get_environment("TACZ_BODY")
	var mag_src := OS.get_environment("TACZ_MAG")
	var tex_path := OS.get_environment("TACZ_TEX")
	var body_out := OS.get_environment("TACZ_BODY_OUT")
	var mag_out := OS.get_environment("TACZ_MAG_OUT")
	if body_src == "" or body_out == "":
		print("缺少 TACZ_BODY / TACZ_BODY_OUT")
		quit(1)
		return

	var mat := StandardMaterial3D.new()
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_PER_PIXEL
	mat.roughness = 0.82
	mat.metallic = 0.0
	mat.specular = 0.2
	mat.cull_mode = BaseMaterial3D.CULL_BACK
	if tex_path != "" and ResourceLoader.exists(tex_path):
		mat.albedo_texture = load(tex_path)

	var body_mesh := _extract(body_src, "gun", mat)
	if body_mesh == null:
		quit(1)
		return
	var err := ResourceSaver.save(body_mesh, body_out)
	print("saved body -> ", body_out, " err=", err)

	if mag_src != "" and mag_out != "":
		var mag_mesh := _extract(mag_src, "mag", mat)
		if mag_mesh != null:
			var err2 := ResourceSaver.save(mag_mesh, mag_out)
			print("saved mag -> ", mag_out, " err=", err2)
	quit(0)

func _extract(glb: String, node_name: String, mat: StandardMaterial3D) -> ArrayMesh:
	if not ResourceLoader.exists(glb):
		print("LOAD FAIL ", glb)
		return null
	var scene: PackedScene = load(glb)
	var inst := scene.instantiate()
	var mi := inst.find_child(node_name, true, false) as MeshInstance3D
	if mi == null or mi.mesh == null:
		print("NODE/MESH NOT FOUND: ", node_name, " in ", glb)
		return null
	var src: Mesh = mi.mesh
	var out := ArrayMesh.new()
	for s in src.get_surface_count():
		var arrays := src.surface_get_arrays(s)
		# 去掉骨骼权重/关节（静态 Mesh 用不到，也避免残留皮肤数据）
		arrays[Mesh.ARRAY_BONES] = null
		arrays[Mesh.ARRAY_WEIGHTS] = null
		var si := out.get_surface_count()
		out.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays, [], {}, 0)
		out.surface_set_material(si, mat)
		print("surface ", s, " verts=", (arrays[Mesh.ARRAY_VERTEX] as PackedVector3Array).size())
	inst.free()
	return out
