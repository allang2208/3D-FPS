extends SceneTree
## Sketchfab low-poly AKM（带骨骼、纯色无贴图）→ 静态 ArrayMesh .tres
## - CPU 蒙皮：把 rest 姿态下的顶点烘焙成世界坐标（绕开 GLB 骨骼渲染路径）
## - 按最高权重骨骼拆分弹匣（mag_02）为独立网格
## - 保留每个部件的材质（深灰金属/木色）
## - 归一化到 1m + 沿枪轴 X 逆时针转 90°（Sketchfab 模型常平放）
## 用法：
##   $env:LP_GLB='res://assets/models/ak/lowpoly_akm/lowpoly_akm.glb'
##   $env:LP_BODY_OUT='res://assets/models/ak/lowpoly_akm/lowpoly_body.tres'
##   $env:LP_MAG_OUT='res://assets/models/ak/lowpoly_akm/lowpoly_mag.tres'

func _init() -> void:
	var glb := OS.get_environment("LP_GLB")
	var body_out := OS.get_environment("LP_BODY_OUT")
	var mag_out := OS.get_environment("LP_MAG_OUT")
	if glb == "" or body_out == "":
		print("缺 LP_GLB / LP_BODY_OUT")
		quit(1)
		return
	var scene: PackedScene = load(glb)
	var inst := scene.instantiate()
	root.add_child(inst)
	var sk := inst.find_child("Skeleton3D", true, false) as Skeleton3D
	if sk == null:
		print("no skeleton")
		quit(1)
		return

	var body_surfaces: Array = []
	var mag_surfaces: Array = []
	for mi in inst.find_children("*", "MeshInstance3D", true, false):
		var mesh: Mesh = mi.mesh
		if mesh == null:
			continue
		var skin: Skin = mi.skin
		for s in mesh.get_surface_count():
			var arrays := mesh.surface_get_arrays(s)
			var mat: Material = mesh.surface_get_material(s)
			if mat is StandardMaterial3D:
				var sm := mat as StandardMaterial3D
				# GLB 材质 baseColorFactor 0.05~0.16 过暗，提亮 2.5 倍保证可读
				sm = sm.duplicate() as StandardMaterial3D
				sm.albedo_color = sm.albedo_color * 2.5
				mat = sm
			_bake_surface(arrays, skin, sk, body_surfaces, mag_surfaces, mat)
		print("baked ", mi.name, " surfaces=", mesh.get_surface_count())

	if body_surfaces.is_empty():
		print("no body")
		quit(1)
		return

	var body_mesh := ArrayMesh.new()
	var body_verts := 0
	for sf in body_surfaces:
		var si := body_mesh.get_surface_count()
		body_mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, sf["arrays"], [], {}, 0)
		body_mesh.surface_set_material(si, sf["mat"])
		body_verts += (sf["arrays"][Mesh.ARRAY_VERTEX] as PackedVector3Array).size()
	var extent := _max_extent(body_surfaces)
	var s := 1.0 / extent if extent > 1e-6 else 1.0
	print("body verts=", body_verts, " extent=", extent, " scale=", s)
	_scale_only(body_surfaces, s)
	_scale_only(mag_surfaces, s)

	var out_body := ArrayMesh.new()
	for sf in body_surfaces:
		var si := out_body.get_surface_count()
		out_body.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, sf["arrays"], [], {}, 0)
		out_body.surface_set_material(si, sf["mat"])
	var err := ResourceSaver.save(out_body, body_out)
	print("saved body ", body_out, " err=", err)

	if not mag_surfaces.is_empty() and mag_out != "":
		var out_mag := ArrayMesh.new()
		for sf in mag_surfaces:
			var si := out_mag.get_surface_count()
			out_mag.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, sf["arrays"], [], {}, 0)
			out_mag.surface_set_material(si, sf["mat"])
		var err2 := ResourceSaver.save(out_mag, mag_out)
		print("saved mag ", mag_out, " err=", err2)
	inst.free()
	quit(0)

func _bake_surface(arrays: Array, skin: Skin, sk: Skeleton3D,
		body_surfaces: Array, mag_surfaces: Array, mat: Material) -> void:
	var verts: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
	var normals: PackedVector3Array = arrays[Mesh.ARRAY_NORMAL]
	var bones = arrays[Mesh.ARRAY_BONES] if arrays[Mesh.ARRAY_BONES] != null else PackedByteArray()
	var weights: PackedFloat32Array = arrays[Mesh.ARRAY_WEIGHTS] if arrays[Mesh.ARRAY_WEIGHTS] != null else PackedFloat32Array()
	var src_idx: PackedInt32Array = arrays[Mesh.ARRAY_INDEX] if arrays[Mesh.ARRAY_INDEX] != null else PackedInt32Array()
	# bone bind idx -> Transform3D(rest_global * bind)
	var xforms: Array[Transform3D] = []
	var bone_names: Array[String] = []
	if skin != null and not bones.is_empty():
		for bi in skin.get_bind_count():
			# Godot glTF 导入：skin bind i 与 skeleton bone i 顺序一致
			var bname: String = sk.get_bone_name(bi) if bi < sk.get_bone_count() else ""
			bone_names.append(bname)
			if bi < sk.get_bone_count():
				xforms.append(sk.get_bone_global_rest(bi) * skin.get_bind_pose(bi))
			else:
				xforms.append(Transform3D.IDENTITY)

	# 烘焙每个顶点 + 记录支配骨骼是否 mag_02
	var baked_pos: Array[Vector3] = []
	var baked_norm: Array[Vector3] = []
	var baked_mag: Array[bool] = []
	for i in verts.size():
		var p := verts[i]
		var n := normals[i] if i < normals.size() else Vector3.UP
		var wp := Vector3.ZERO
		var wn := Vector3.ZERO
		var dom_name := ""
		var domw := 0.0
		for b in 4:
			var bi := int(bones[i * 4 + b]) if bones.size() > i * 4 + b else 0
			var w := weights[i * 4 + b] if weights.size() > i * 4 + b else 0.0
			if w <= 0.0:
				continue
			if bi < xforms.size():
				var t := xforms[bi]
				wp += t * p * w
				wn += t.basis * n * w
			if w > domw:
				domw = w
				dom_name = bone_names[bi] if bi < bone_names.size() else ""
		baked_pos.append(wp)
		baked_norm.append(wn.normalized())
		baked_mag.append(dom_name == "mag_02")

	# 按三角形拆分，保留连接
	var body_v := PackedVector3Array()
	var body_n := PackedVector3Array()
	var body_idx := PackedInt32Array()
	var mag_v := PackedVector3Array()
	var mag_n := PackedVector3Array()
	var mag_idx := PackedInt32Array()
	var tri_count := src_idx.size() / 3 if not src_idx.is_empty() else verts.size() / 3
	for t in tri_count:
		var a := int(src_idx[t * 3]) if not src_idx.is_empty() else t * 3
		var b := int(src_idx[t * 3 + 1]) if not src_idx.is_empty() else t * 3 + 1
		var c := int(src_idx[t * 3 + 2]) if not src_idx.is_empty() else t * 3 + 2
		var is_mag := baked_mag[a] or baked_mag[b] or baked_mag[c]
		for corner in [a, b, c]:
			if is_mag:
				mag_idx.append(mag_v.size())
				mag_v.append(baked_pos[corner])
				mag_n.append(baked_norm[corner])
			else:
				body_idx.append(body_v.size())
				body_v.append(baked_pos[corner])
				body_n.append(baked_norm[corner])
	if body_v.size() > 0:
		body_surfaces.append(_surface(body_v, body_n, body_idx, mat))
	if mag_v.size() > 0:
		mag_surfaces.append(_surface(mag_v, mag_n, mag_idx, mat))

func _surface(v: PackedVector3Array, n: PackedVector3Array, idx: PackedInt32Array, mat: Material) -> Dictionary:
	var arrays: Array = []
	arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX] = v
	arrays[Mesh.ARRAY_NORMAL] = n
	if not idx.is_empty():
		arrays[Mesh.ARRAY_INDEX] = idx
	return {"arrays": arrays, "mat": mat}

func _max_extent(surfaces: Array) -> float:
	var mn := Vector3(INF, INF, INF)
	var mx := Vector3(-INF, -INF, -INF)
	for sf in surfaces:
		var v: PackedVector3Array = sf["arrays"][Mesh.ARRAY_VERTEX]
		for p in v:
			mn = mn.min(p)
			mx = mx.max(p)
	var e := mx - mn
	return maxf(maxf(e.x, e.y), e.z)

func _scale_only(surfaces: Array, s: float) -> void:
	for sf in surfaces:
		var v: PackedVector3Array = sf["arrays"][Mesh.ARRAY_VERTEX]
		var n: PackedVector3Array = sf["arrays"][Mesh.ARRAY_NORMAL]
		for i in v.size():
			var p := v[i]
			# 归一化 + 绕枪轴(Z)逆时针-90°：机匣顶从侧面转到朝上（否则"水平放置"）
			v[i] = Vector3(p.y, -p.x, p.z) * s
			var nn := n[i]
			n[i] = Vector3(nn.y, -nn.x, nn.z).normalized()
		sf["arrays"][Mesh.ARRAY_VERTEX] = v
		sf["arrays"][Mesh.ARRAY_NORMAL] = n
