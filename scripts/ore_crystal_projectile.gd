@static_unload
extends Node3D
## Fixed landing point, one-second arc, swept wall collision and one ground hit.
signal impacted(point: Vector3)
var start := Vector3.ZERO
var landing := Vector3.ZERO
var flight_seconds := 1.0
var arc_height := 1.4
var radius := 1.4
var damage := 56
var target: WeakRef
var source: WeakRef
var elapsed := 0.0
var spent := false
var warning: MeshInstance3D
var crystal: Node3D
static var rock_mesh: ArrayMesh
static var rock_material: StandardMaterial3D

static func ring(parent: Node3D, point: Vector3, size: float, color: Color) -> MeshInstance3D:
	var visual := MeshInstance3D.new()
	var mesh := TorusMesh.new()
	mesh.inner_radius = maxf(.01, size - .035)
	mesh.outer_radius = size + .035
	mesh.rings = 48
	mesh.ring_segments = 6
	visual.mesh = mesh
	var mat := StandardMaterial3D.new()
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	mat.albedo_color = color
	visual.material_override = mat
	parent.add_child(visual)
	visual.global_position = point + Vector3(0, .035, 0)
	visual.scale.y = .35
	return visual

static func can_hit(world: Node3D, point: Vector3, victim: Node3D, size: float) -> bool:
	if not is_instance_valid(victim) or victim.get("is_dead") == true: return false
	var offset := victim.global_position - point
	if absf(offset.y) > 1.2 or Vector2(offset.x, offset.z).length() > size: return false
	var ray := PhysicsRayQueryParameters3D.create(point + Vector3.UP * .35, victim.global_position + Vector3.UP * .35, 1)
	return world.get_world_3d().direct_space_state.intersect_ray(ray).is_empty()

static func make_crystal() -> MeshInstance3D:
	var visual := MeshInstance3D.new()
	if not rock_mesh:
		var base := SphereMesh.new()
		base.radius = .29
		base.height = .52
		base.radial_segments = 9
		base.rings = 4
		var arrays := base.get_mesh_arrays()
		var vertices: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
		var indices: PackedInt32Array = arrays[Mesh.ARRAY_INDEX]
		var surface := SurfaceTool.new()
		surface.begin(Mesh.PRIMITIVE_TRIANGLES)
		# Coordinate-based distortion keeps duplicate seam vertices welded.
		for i in range(0, indices.size(), 3):
			var points: Array[Vector3] = []
			for j in 3:
				var v := vertices[indices[i + j]]
				v *= 1.0 + .18 * sin(v.x * 31.0 + v.y * 19.0 + v.z * 27.0)
				points.append(v * Vector3(1.2, .88, 1.0))
			var normal := (points[2] - points[0]).cross(points[1] - points[0]).normalized()
			var ore := (i / 3) % 7 == 0 or (i / 3) % 11 == 0
			var color := Color(.37, .19, .48) if ore else Color(.25, .23, .26)
			color *= .82 + .27 * absf(sin(float(i) * 1.7))
			color.a = 1.0
			for v in points:
				surface.set_normal(normal)
				surface.set_color(color)
				surface.add_vertex(v)
		rock_mesh = surface.commit()
		rock_material = StandardMaterial3D.new()
		rock_material.vertex_color_use_as_albedo = true
		rock_material.roughness = .94
	visual.mesh = rock_mesh
	visual.material_override = rock_material
	return visual

func _ready() -> void:
	global_position = start
	crystal = make_crystal()
	add_child(crystal)
	warning = ring(get_parent(), landing, radius, Color(.85, .12, .22))

func arc_point(t: float) -> Vector3:
	return start.lerp(landing, t) + Vector3.UP * (4.0 * arc_height * t * (1.0 - t))

func _physics_process(delta: float) -> void:
	if spent: return
	# Subdivide the curved path even if a slow frame spans the entire flight.
	var end_time := minf(elapsed + delta, flight_seconds)
	while elapsed < end_time:
		var next := minf(elapsed + 1.0 / 60.0, end_time)
		var point := arc_point(next / flight_seconds)
		var ray := PhysicsRayQueryParameters3D.create(global_position, point, 1)
		var hit := get_world_3d().direct_space_state.intersect_ray(ray)
		elapsed = next
		if not hit.is_empty():
			global_position = hit.position
			# Walls absorb the stone; floor contact near the destination explodes.
			_finish(hit.normal.y > .6 and global_position.distance_to(landing) < .3)
			return
		global_position = point
	crystal.rotation = Vector3(elapsed * TAU, elapsed * .8, .4)
	if elapsed >= flight_seconds: _finish(true)

func _finish(deal_damage: bool) -> void:
	if spent: return
	spent = true
	var victim: Node3D = target.get_ref() if target else null
	if deal_damage and can_hit(self, landing, victim, radius):
		victim.take_damage(damage, "physical", source.get_ref() if source else null)
	if deal_damage:
		var impact := Node3D.new()
		impact.set_script(load("res://scripts/ore_rock_impact.gd"))
		# The monster owns effects so room cleanup cannot strand transient nodes.
		var owner_node: Node3D = source.get_ref() if source else null
		(owner_node if is_instance_valid(owner_node) else get_parent()).add_child(impact)
		impact.top_level = true
		impact.global_position = global_position
	impacted.emit(global_position)
	queue_free()

func _exit_tree() -> void:
	if is_instance_valid(warning): warning.queue_free()
