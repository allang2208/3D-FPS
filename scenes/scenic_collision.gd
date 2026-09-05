extends RefCounted

## Collision helpers for the authored landscape. Shapes store scaled vertices;
## physics nodes themselves always have unit scale.
static func mesh_points(root: Node3D, woody_only := false, underside_only := false) -> PackedVector3Array:
	var points := PackedVector3Array()
	var to_root := root.global_transform.affine_inverse()
	for child in root.find_children("", "MeshInstance3D", true, false):
		var mesh: Mesh = child.mesh
		var xf: Transform3D = to_root * child.global_transform
		for surface in mesh.get_surface_count():
			var mat: Material = child.get_active_material(surface)
			var material_name := mat.resource_name.to_lower() if mat != null else ""
			if woody_only and ("leaves" in material_name or "twig" in material_name or "canopy_branches" in material_name):
				continue
			var arrays := mesh.surface_get_arrays(surface)
			var vertices: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
			var normals: PackedVector3Array = arrays[Mesh.ARRAY_NORMAL]
			for i in vertices.size():
				if underside_only and (xf.basis.inverse().transposed() * normals[i]).normalized().y > -0.1:
					continue
				points.append(xf * vertices[i])
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
		var ix := clampi(int((point.x - box.position.x) / maxf(box.size.x, 0.001) * 32), 0, 31)
		var iz := clampi(int((point.z - box.position.z) / maxf(box.size.z, 0.001) * 32), 0, 31)
		var key := Vector2i(ix, iz)
		if not cells.has(key) or point.y < cells[key].y:
			cells[key] = point
	# Include downward-facing surfaces even above the lowest 38%: high overhang
	# lips were invisible to the old height-band-only check.
	var underside := mesh_points(root, false, true)
	for point in cells.values():
		underside.append(point)
	return {"hull": hull_points(points), "support": underside, "bounds": box}


static func root_geometry(model: Node3D, tree := false) -> Dictionary:
	var points := mesh_points(model, tree)
	var box := bounds(points)
	var support := PackedVector3Array()
	# Single-plant geometry only. Low wood excludes foliage when locating trees.
	for point in points:
		if point.y <= box.position.y + box.size.y * (0.025 if tree else 0.08):
			support.append(point)
	var root_box := bounds(support)
	var anchor := root_box.get_center()
	anchor.y = box.position.y
	var clearance := PackedVector3Array()
	for i in range(0, points.size(), maxi(1, ceili(points.size() / 256.0))):
		if points[i].y > box.position.y + box.size.y * 0.2:
			clearance.append(points[i])
	return {"support": support, "anchor": anchor, "bounds": box, "clearance": clearance}


static func fit_root(data: Terrain3DData, at: Vector2, factor: float, yaw: float, geometry: Dictionary, tree := false) -> Dictionary:
	var center := Vector3(at.x, 0, at.y)
	var h := data.get_height(center)
	var dx := data.get_height(center + Vector3.RIGHT * 0.5) - data.get_height(center - Vector3.RIGHT * 0.5)
	var dz := data.get_height(center + Vector3.BACK * 0.5) - data.get_height(center - Vector3.BACK * 0.5)
	var normal := Vector3(-dx, 1, -dz).normalized()
	if not is_finite(h) or normal.y < cos(deg_to_rad(38 if tree else 32)):
		return {}
	var basis := Basis(Vector3.UP, yaw)
	if not tree:
		basis = Basis(Quaternion(Vector3.UP, normal)) * basis
	basis = basis.scaled(Vector3.ONE * factor)
	var anchor: Vector3 = geometry["anchor"]
	center -= basis * Vector3(anchor.x, 0, anchor.z)
	var low := INF
	var high := -INF
	for point in geometry["support"]:
		var rotated: Vector3 = basis * point
		var ground := data.get_height(center + Vector3(rotated.x, 0, rotated.z))
		if not is_finite(ground):
			return {}
		low = minf(low, ground - rotated.y)
		high = maxf(high, ground - rotated.y)
	var height: float = geometry["bounds"].size.y * factor
	if high - low > minf(0.65, height * (0.12 if tree else 0.3)):
		return {}
	center.y = low - clampf(height * 0.035, 0.015, 0.12)
	var xf := Transform3D(basis, center)
	var buried := 0
	for point in geometry["clearance"]:
		var world: Vector3 = xf * point
		if world.y < data.get_height(world) - 0.025:
			buried += 1
	if buried > geometry["clearance"].size() * 0.08:
		return {}
	return {"transform": xf, "root_spread": high - low}


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
