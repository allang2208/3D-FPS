extends Node3D
@export var kind := "flashlight"
var _gun: Node3D
var _dot: MeshInstance3D
var _beam: MeshInstance3D
const LASER_RANGE := 80.0

func _ready() -> void:
	# Gun advances the viewmodel in _process; draw from that same frame's pose.
	process_priority = 100
	var ancestor := get_parent()
	while ancestor != null:
		if ancestor.has_method("hipfire_radius_pixels"):
			_gun = ancestor
			break
		ancestor = ancestor.get_parent()
	if kind == "laser":
		_dot = MeshInstance3D.new()
		_dot.name = "LaserImpact"
		var sphere := SphereMesh.new()
		sphere.radius = 0.008
		sphere.height = 0.016
		sphere.radial_segments = 12
		sphere.rings = 6
		_dot.mesh = sphere
		var mat := StandardMaterial3D.new()
		mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
		mat.albedo_color = Color(1, 0.04, 0.015)
		mat.emission_enabled = true
		mat.emission = mat.albedo_color
		mat.emission_energy_multiplier = 3.0
		_dot.material_override = mat
		_dot.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		add_child(_dot)
		_dot.top_level = true
		_dot.hide()
		_beam = MeshInstance3D.new()
		_beam.name = "LaserBeam"
		var cylinder := CylinderMesh.new()
		cylinder.top_radius = 0.002
		cylinder.bottom_radius = 0.002
		cylinder.height = 1.0
		cylinder.radial_segments = 12
		_beam.mesh = cylinder
		var beam_material: StandardMaterial3D = mat.duplicate()
		beam_material.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
		beam_material.albedo_color = Color(1.0, 0.015, 0.005, 0.65)
		_beam.material_override = beam_material
		_beam.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		add_child(_beam)
		_beam.top_level = true
		_beam.hide()
	if _gun == null:
		var light := get_node_or_null("Emitter/SpotLight3D")
		if light != null:
			light.hide()
		set_process(false)

func _emitter_transform() -> Transform3D:
	var emitter := get_node("Emitter") as Node3D
	var relative := emitter.transform
	var ancestor := emitter.get_parent()
	while ancestor is Node3D:
		if ancestor is BoneAttachment3D and ancestor.get_parent() is Skeleton3D:
			var rig := ancestor.get_parent() as Skeleton3D
			return rig.global_transform * rig.get_bone_global_pose(ancestor.bone_idx) * relative
		relative = ancestor.transform * relative
		ancestor = ancestor.get_parent()
	return emitter.global_transform

func _process(_delta: float) -> void:
	if _dot == null:
		return
	_dot.hide()
	_beam.hide()
	if not is_visible_in_tree() or not _gun.inventory_active:
		return
	# Hip fire keeps the physical emitter axis. ADS converges on the visible reticle.
	var emitter_pose := _emitter_transform()
	var emitter := emitter_pose.origin
	var ray_direction := -emitter_pose.basis.orthonormalized().z
	var space := get_world_3d().direct_space_state
	if _gun._ads:
		var camera: Camera3D = _gun._camera()
		if camera != null:
			var screen: Vector2 = _gun.aim_screen_position(camera)
			var origin := camera.project_ray_origin(screen)
			var target := origin + camera.project_ray_normal(screen) * LASER_RANGE
			var aim_hit := space.intersect_ray(PhysicsRayQueryParameters3D.create(origin, target, 3))
			if not aim_hit.is_empty():
				target = aim_hit.position
			if emitter.distance_squared_to(target) > 0.000001:
				ray_direction = (target - emitter).normalized()
	var end := emitter + ray_direction * LASER_RANGE
	var hit := space.intersect_ray(PhysicsRayQueryParameters3D.create(emitter, end, 3))
	if not hit.is_empty():
		end = hit.position
		_dot.global_position = hit.position + hit.normal * 0.003
		_dot.show()
	var length := emitter.distance_to(end)
	if length > 0.001:
		var direction := (end - emitter) / length
		var up := Vector3.RIGHT if absf(direction.dot(Vector3.UP)) > 0.99 else Vector3.UP
		var beam_basis := Basis.looking_at(direction, up) * Basis(Vector3.RIGHT, PI * 0.5)
		_beam.global_transform = Transform3D(beam_basis.scaled_local(Vector3(1.0, length, 1.0)), emitter.lerp(end, 0.5))
		_beam.show()
