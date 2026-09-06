extends SceneTree
## Offline silhouette sculpting of the two existing CC0 Poly Haven scans.
const NAMES = ["rounded", "slab", "leaning", "ridge", "wedge", "saddle", "tall", "long"]
func _initialize() -> void: call_deferred("run")
func sculpt(p: Vector3, variant: int) -> Vector3:
	var q := p
	match variant:
		0: q *= Vector3(1.0, 1.15, 0.9)
		1: q *= Vector3(1.0, 0.42, 0.85)
		2:
			q *= Vector3(0.65, 1.7, 0.72)
			q.x += p.y * 0.45
		3:
			q.y *= 0.55 + 1.65 * exp(-pow(p.x * 3.2, 2))
			q.z *= 0.7
		4:
			q.y *= 0.35 + (p.x + 0.5) * 1.65
			q.z *= 0.8
		5:
			q.y *= 1.6 - 1.15 * exp(-pow(p.x * 4.5, 2))
			q.z *= 0.72
		6:
			q *= Vector3(0.65, 1.8, 0.65)
			q.x += 0.12 * sin(p.y * 6.0)
		7:
			q *= Vector3(1.0, 0.7, 0.44)
			q.z += 0.15 * sin(p.x * 5.0)
	return q
func run() -> void:
	for variant in NAMES.size():
		var source_name: String = "boulder_01" if variant % 2 == 0 else "rock_09"
		var source_path := "res://assets/models/polyhaven/%s/%s_2k.gltf" % [source_name, source_name]
		var source: Node3D = load(source_path).instantiate()
		root.add_child(source)
		var box: AABB = load("res://scenes/scenic_collision.gd").rock_geometry(source).bounds
		var divisor := maxf(box.size.x, box.size.z)
		var origin := Vector3(box.get_center().x, box.position.y, box.get_center().z)
		var model := Node3D.new()
		model.name = NAMES[variant]
		root.add_child(model)
		var parts: Array = []
		for child in source.find_children("", "MeshInstance3D", true, false):
			var mesh := ArrayMesh.new()
			var xf: Transform3D = source.global_transform.affine_inverse() * child.global_transform
			for surface in child.mesh.get_surface_count():
				var st := SurfaceTool.new()
				st.create_from(child.mesh, surface)
				st.deindex()
				var arrays := st.commit_to_arrays()
				var points: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
				for i in points.size(): points[i] = sculpt((xf * points[i] - origin) / divisor, variant)
				arrays[Mesh.ARRAY_VERTEX] = points
				arrays[Mesh.ARRAY_NORMAL] = null
				arrays[Mesh.ARRAY_TANGENT] = null
				var raw := ArrayMesh.new()
				raw.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
				st = SurfaceTool.new()
				st.create_from(raw, 0)
				st.generate_normals()
				st.generate_tangents()
				st.index()
				var mat: StandardMaterial3D = child.get_active_material(surface).duplicate()
				if mat.albedo_texture == null: mat.albedo_texture = load(source_path.get_base_dir()+"/textures/"+source_name+"_diff_2k.jpg")
				st.set_material(mat)
				st.commit(mesh)
			var mi := MeshInstance3D.new()
			mi.mesh = mesh
			model.add_child(mi)
			mi.owner = model
			parts.append({"mesh": mesh, "transform": Transform3D.IDENTITY})
		var folder: String = "res://assets/models/ore_variants/"+NAMES[variant]+"/"
		DirAccess.make_dir_recursive_absolute(folder)
		var packed := PackedScene.new()
		assert(packed.pack(model) == OK)
		assert(ResourceSaver.save(packed, folder+"model.scn") == OK)
		var pieces: Array = load("res://scripts/tools/rock_fracture_mesh.gd").fracture(parts)
		assert(pieces.size() == 8)
		for piece in pieces:
			piece["hull"] = piece.mesh.create_convex_shape(true, false).points
		var baked := Resource.new()
		baked.set_meta("pieces", pieces)
		assert(ResourceSaver.save(baked, folder+"fragments.res") == OK)
		print("ORE_VARIANT ", NAMES[variant], " pieces=", pieces.size())
		model.free()
		source.free()
	quit()
