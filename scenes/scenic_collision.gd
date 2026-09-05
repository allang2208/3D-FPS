extends RefCounted

## Collision helpers for the authored landscape. Shapes store scaled vertices;
## physics nodes themselves always have unit scale.
static func mesh_points(root: Node3D, woody_only := false) -> PackedVector3Array:
	var points := PackedVector3Array()
	var to_root := root.global_transform.affine_inverse()
	for child in root.find_children("", "MeshInstance3D", true, false):
		var mesh: Mesh = child.mesh
		var xf: Transform3D = to_root * child.global_transform
		for surface in mesh.get_surface_count():
			var mat: Material = child.get_active_material(surface)
			var material_name := mat.resource_name.to_lower() if mat != null else ""
			if woody_only and ("leaves" in material_name or "twigs" in material_name):
				continue
			var vertices: PackedVector3Array = mesh.surface_get_arrays(surface)[Mesh.ARRAY_VERTEX]
			for vertex in vertices:
				points.append(xf * vertex)
	return points


static func bounds(points: PackedVector3Array) -> AABB:
	var box := AABB(points[0], Vector3.ZERO)
	for point in points:
		box = box.expand(point)
	return box


static func hull_points(points: PackedVector3Array) -> PackedVector3Array:
	var arrays := []
	arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX] = points
	var mesh := ArrayMesh.new()
	mesh.add_surface_from_arrays(Mesh.PRIMITIVE_POINTS, arrays)
	# Clean/QuickHull accepts a point cloud; V-HACD simplification needs triangles.
	var hull := mesh.create_convex_shape(true, false)
	return hull.points


static func rock_geometry(root: Node3D) -> Dictionary:
	var points := mesh_points(root)
	var box := bounds(points)
	# Lower-envelope samples retain the real mesh underside, including the lip of
	# open-bottom scans. Unlike an AABB corner, each sample is actual rock geometry.
	var cells: Dictionary = {}
	for point in points:
		if point.y > box.position.y + box.size.y * 0.38:
			continue
		var ix := clampi(int((point.x - box.position.x) / maxf(box.size.x, 0.001) * 16), 0, 15)
		var iz := clampi(int((point.z - box.position.z) / maxf(box.size.z, 0.001) * 16), 0, 15)
		var key := Vector2i(ix, iz)
		if not cells.has(key) or point.y < cells[key].y:
			cells[key] = point
	var underside := PackedVector3Array()
	for point in cells.values():
		underside.append(point)
	return {"hull": hull_points(points), "support": underside, "bounds": box}


static func fit_rock(data: Terrain3DData, at: Vector2, scale_factor: float, yaw: float, geometry: Dictionary) -> Transform3D:
	var size: Vector3 = geometry["bounds"].size * scale_factor
	var step := maxf(0.5, maxf(size.x, size.z) * 0.25)
	var center := Vector3(at.x, 0, at.y)
	var dx := (data.get_height(center + Vector3(step, 0, 0)) - data.get_height(center - Vector3(step, 0, 0))) / (2.0 * step)
	var dz := (data.get_height(center + Vector3(0, 0, step)) - data.get_height(center - Vector3(0, 0, step))) / (2.0 * step)
	var normal := Vector3(-dx, 1.0, -dz).normalized()
	var angle := Vector3.UP.angle_to(normal)
	if angle > deg_to_rad(35):
		normal = Vector3.UP.slerp(normal, deg_to_rad(35) / angle)
	var basis := (Basis(Quaternion(Vector3.UP, normal)) * Basis(Vector3.UP, yaw)).scaled(Vector3.ONE * scale_factor)
	var lowest_origin := INF
	for point in geometry["support"]:
		var rotated: Vector3 = basis * point
		var ground := data.get_height(center + Vector3(rotated.x, 0, rotated.z))
		lowest_origin = minf(lowest_origin, ground - rotated.y)
	center.y = lowest_origin - clampf(size.y * 0.08, 0.05, 0.3)
	return Transform3D(basis, center)


static func add_rock(parent: Node3D, xf: Transform3D, geometry: Dictionary) -> StaticBody3D:
	var body := StaticBody3D.new()
	body.name = "LandscapeRock"
	body.collision_layer = 1
	body.collision_mask = 0
	body.set_meta("impact_surface", "concrete")
	body.add_to_group("scenic_rocks")
	parent.add_child(body)
	body.position = xf.origin
	var vertices := PackedVector3Array()
	for point in geometry["hull"]:
		vertices.append(xf.basis * point)
	var shape := ConvexPolygonShape3D.new()
	shape.points = vertices
	shape.margin = 0.015
	var collision := CollisionShape3D.new()
	collision.shape = shape
	body.add_child(collision)
	var support := PackedVector3Array()
	for point in geometry["support"]:
		support.append(xf.basis * point)
	body.set_meta("underside_points", support)
	body.set_meta("local_bounds", bounds(vertices))
	return body


static func trunk_hulls(model: Node3D) -> Array[PackedVector3Array]:
	var points := mesh_points(model, true)
	var box := bounds(points)
	var result: Array[PackedVector3Array] = []
	# Three closed bands follow lean and root flare without making the crown solid.
	var top := box.position.y + box.size.y * 0.38
	for band in 3:
		var bottom := lerpf(box.position.y, top, band / 3.0)
		var ceiling := lerpf(box.position.y, top, (band + 1) / 3.0)
		var subset := PackedVector3Array()
		for point in points:
			if point.y >= bottom - box.size.y * 0.012 and point.y <= ceiling + box.size.y * 0.012:
				subset.append(point)
		if subset.size() >= 4:
			result.append(hull_points(subset))
	return result


static func add_trunk(body: StaticBody3D, model_xf: Transform3D, hulls: Array[PackedVector3Array]) -> void:
	body.collision_layer = 1
	body.collision_mask = 0
	body.add_to_group("scenic_trees")
	for points in hulls:
		var shape := ConvexPolygonShape3D.new()
		var vertices := PackedVector3Array()
		for point in points:
			vertices.append(model_xf * point)
		shape.points = vertices
		shape.margin = 0.015
		var collision := CollisionShape3D.new()
		collision.shape = shape
		body.add_child(collision)
