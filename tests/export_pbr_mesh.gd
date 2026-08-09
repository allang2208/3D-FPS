# 把 OBJ 导入的网格材质补上 metallic/roughness/AO（按命名约定 xxx_metallic.png 等），
# 导出为 .tscn 场景：$env:PBR_MESH=源网格，$env:PBR_OUT=输出场景
extends SceneTree

func _process(_d) -> bool:
	var src := OS.get_environment("PBR_MESH")
	if src == "":
		print("用法: 设置 PBR_MESH=res://assets/models/xxx.obj PBR_OUT=res://assets/models/xxx.tscn")
		quit(1)
		return false
	var mesh: ArrayMesh = load(src)
	if mesh == null:
		print("LOAD FAIL ", src)
		quit(1)
		return false
	var body_mesh := ArrayMesh.new()
	var mag_mesh := ArrayMesh.new()
	for i in range(mesh.get_surface_count()):
		var mat: StandardMaterial3D = mesh.surface_get_material(i)
		var is_mag: bool = mat != null and mat.albedo_texture != null \
			and mat.albedo_texture.resource_path.get_file().begins_with("mag_")
		var target := mag_mesh if is_mag else body_mesh
		var si := target.get_surface_count()
		if mat == null or mat.albedo_texture == null:
			target.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, mesh.surface_get_arrays(i), [], {}, 0)
			continue
		var stem := mat.albedo_texture.resource_path.get_basename()
		if stem.ends_with("_basecolor"):
			stem = stem.trim_suffix("_basecolor")
		mat.metallic_texture = _tex(stem + "_metallic.png")
		mat.roughness_texture = _tex(stem + "_roughness.png")
		var ao_tex := _tex(stem + "_ao.png")
		if ao_tex != null:
			mat.ao_enabled = true
			mat.ao_texture = ao_tex
		target.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, mesh.surface_get_arrays(i), [], {}, 0)
		target.surface_set_material(si, mat)
		print("patched surf ", i, " stem=", stem, " -> ", "mag" if is_mag else "body")
	var out := OS.get_environment("PBR_OUT")
	if out != "":
		var err := ResourceSaver.save(body_mesh, out)
		print("saved body ", out, " err=", err)
	var mag_out := OS.get_environment("PBR_MAG_OUT")
	if mag_out != "" and mag_mesh.get_surface_count() > 0:
		var err2 := ResourceSaver.save(mag_mesh, mag_out)
		print("saved mag ", mag_out, " err=", err2)
	quit(0)
	return false

func _tex(res: String) -> Texture2D:
	if not ResourceLoader.exists(res):
		return null
	return load(res)
