extends SceneTree
## Sketchfab AKM GLB（分件：左右半枪/弹匣/抛壳/扳机）→ 静态 ArrayMesh .tres
## - 所有非弹匣网格合并为枪体，弹匣网格独立为 mag
## - 网格按枪体 AABB 长轴归一化到 1m（gun.gd 视模缩放有 clampf 下限 0.4）
## - PBR 贴图：akm_*/magazine_*（PBR 套件，含 OpenGL 法线）
## 用法：
##   $env:AKM_GLB='res://assets/models/ak/akm_glb/akm.glb'
##   $env:AKM_TEX='res://assets/models/ak/akm_glb/tex'
##   $env:AKM_BODY_OUT='res://assets/models/ak/akm_glb/akm_body.tres'
##   $env:AKM_MAG_OUT='res://assets/models/ak/akm_glb/akm_mag.tres'

func _init() -> void:
	var glb := OS.get_environment("AKM_GLB")
	var tex := OS.get_environment("AKM_TEX")
	var body_out := OS.get_environment("AKM_BODY_OUT")
	var mag_out := OS.get_environment("AKM_MAG_OUT")
	if glb == "" or body_out == "":
		print("缺 AKM_GLB / AKM_BODY_OUT")
		quit(1)
		return
	var scene: PackedScene = load(glb)
	var inst := scene.instantiate()

	# 收集所有网格，弹匣单独
	var body_arrays: Array[Array] = []
	var mag_arrays: Array[Array] = []
	for mi in inst.find_children("*", "MeshInstance3D", true, false):
		var mesh: Mesh = mi.mesh
		if mesh == null:
			continue
		var is_mag: bool = mi.name.to_lower().contains("magazine")
		var surf_verts := 0
		for s in mesh.get_surface_count():
			var src := mesh.surface_get_arrays(s)
			var arrays: Array = []
			arrays.resize(Mesh.ARRAY_MAX)
			arrays[Mesh.ARRAY_VERTEX] = src[Mesh.ARRAY_VERTEX]
			arrays[Mesh.ARRAY_NORMAL] = src[Mesh.ARRAY_NORMAL]
			arrays[Mesh.ARRAY_TEX_UV] = src[Mesh.ARRAY_TEX_UV]
			arrays[Mesh.ARRAY_INDEX] = src[Mesh.ARRAY_INDEX]
			surf_verts += (arrays[Mesh.ARRAY_VERTEX] as PackedVector3Array).size()
			if is_mag:
				mag_arrays.append(arrays)
			else:
				body_arrays.append(arrays)
		print("node ", mi.name, " -> ", "mag" if is_mag else "body", " verts=", surf_verts)

	if body_arrays.is_empty():
		print("no body mesh")
		quit(1)
		return

	# 枪体长轴归一化到 1m
	var extent := _max_extent(body_arrays)
	var s := 1.0 / extent if extent > 1e-6 else 1.0
	print("body extent=", extent, " normalize scale=", s)
	for arrays in body_arrays:
		_scale_arrays(arrays, s)
	for arrays in mag_arrays:
		_scale_arrays(arrays, s)

	var body_mesh := ArrayMesh.new()
	var mat := _make_mat(tex, "akm_")
	for arrays in body_arrays:
		var si := body_mesh.get_surface_count()
		body_mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays, [], {}, 0)
		body_mesh.surface_set_material(si, mat)
	var err := ResourceSaver.save(body_mesh, body_out)
	print("saved body ", body_out, " err=", err)

	if not mag_arrays.is_empty() and mag_out != "":
		var mag_mesh := ArrayMesh.new()
		var mmat := _make_mat(tex, "magazine_")
		for arrays in mag_arrays:
			var si := mag_mesh.get_surface_count()
			mag_mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays, [], {}, 0)
			mag_mesh.surface_set_material(si, mmat)
		var err2 := ResourceSaver.save(mag_mesh, mag_out)
		print("saved mag ", mag_out, " err=", err2)
	inst.free()
	quit(0)

func _make_mat(tex: String, prefix: String) -> StandardMaterial3D:
	var m := StandardMaterial3D.new()
	m.shading_mode = BaseMaterial3D.SHADING_MODE_PER_PIXEL
	m.albedo_texture = _load(tex + "/" + prefix + "basecolor.png")
	m.normal_enabled = true
	m.normal_texture = _load(tex + "/" + prefix + "normal.png")
	m.metallic_texture = _load(tex + "/" + prefix + "metallic.png")
	m.roughness_texture = _load(tex + "/" + prefix + "roughness.png")
	m.ao_enabled = true
	m.ao_texture = _load(tex + "/" + prefix + "ao.png")
	return m

func _load(p: String) -> Texture2D:
	if ResourceLoader.exists(p):
		return load(p)
	print("TEX MISSING ", p)
	return null

func _max_extent(arrays_list: Array[Array]) -> float:
	var mn := Vector3(INF, INF, INF)
	var mx := Vector3(-INF, -INF, -INF)
	for arrays in arrays_list:
		var v: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
		for p in v:
			mn = mn.min(p)
			mx = mx.max(p)
	var e := mx - mn
	return maxf(maxf(e.x, e.y), e.z)

func _scale_arrays(arrays: Array, s: float) -> void:
	var v: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
	for i in v.size():
		v[i] = v[i] * s
	arrays[Mesh.ARRAY_VERTEX] = v
