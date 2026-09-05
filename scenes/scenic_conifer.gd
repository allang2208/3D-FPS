extends Node3D

@export var variant := 0
static var templates: Dictionary = {}

func _ready() -> void:
	if not templates.has(variant):
		templates[variant] = _make_meshes(variant)
	for mesh in templates[variant]:
		var node := MeshInstance3D.new()
		node.mesh = mesh
		add_child(node)


static func _tube(st: SurfaceTool, start: Vector3, end: Vector3, radius: float, tip: float) -> void:
	var up := (end - start).normalized()
	var right := up.cross(Vector3.FORWARD).normalized()
	var forward := right.cross(up).normalized()
	for i in 7:
		var a := (right * cos(TAU * i / 7) + forward * sin(TAU * i / 7))
		var b := (right * cos(TAU * (i + 1) / 7) + forward * sin(TAU * (i + 1) / 7))
		var vertices := [start + a * radius, end + a * tip, start + b * radius, start + b * radius, end + a * tip, end + b * tip]
		for j in 6:
			st.set_normal(a if j < 2 or j == 4 else b)
			st.set_uv(Vector2(i / 7.0, 0 if j in [0, 2, 3] else start.distance_to(end)))
			st.add_vertex(vertices[j])


static func _sprig(st: SurfaceTool, start: Vector3, direction: Vector3, length: float, tint: Color) -> void:
	var along := direction.normalized()
	var side := along.cross(Vector3.UP).normalized()
	for crossed in 2:
		var across := side if crossed == 0 else along.cross(side).normalized()
		var positions := [start - across * length * 0.28, start + across * length * 0.28,
			start + along * length - across * length * 0.28, start + along * length + across * length * 0.28]
		var uvs := [Vector2(0.006, 0.443), Vector2(0.246, 0.443), Vector2(0.006, 0.01), Vector2(0.246, 0.01)]
		for index in [0, 2, 1, 1, 2, 3]:
			st.set_color(tint)
			st.set_uv(uvs[index])
			st.set_normal((along.cross(across) + Vector3.UP * 0.65).normalized())
			st.add_vertex(positions[index])


static func _make_meshes(seed_offset: int) -> Array[ArrayMesh]:
	var random := RandomNumberGenerator.new()
	random.seed = 88421 + seed_offset * 317
	var trunk := SurfaceTool.new()
	var branches := SurfaceTool.new()
	var leaves := SurfaceTool.new()
	for st in [trunk, branches, leaves]:
		st.begin(Mesh.PRIMITIVE_TRIANGLES)
	for section in 10:
		_tube(trunk, Vector3(0, section, 0), Vector3(0, section + 1, 0),
			lerpf(0.22, 0.012, section / 10.0), lerpf(0.22, 0.012, (section + 1) / 10.0))
	for tier in 13:
		var y := 2.2 + tier * 0.57
		var reach := lerpf(2.9, 0.3, tier / 12.0)
		var phase := tier * 2.399963 + seed_offset
		for branch in 7:
			var angle := phase + branch * TAU / 7 + random.randf_range(-0.2, 0.2)
			var radial := Vector3(cos(angle), 0, sin(angle))
			var across := Vector3(-radial.z, 0, radial.x)
			var length := reach * random.randf_range(0.8, 1.15)
			var root := Vector3(0, y + random.randf_range(-0.2, 0.2), 0)
			var end := root + radial * length + Vector3.UP * random.randf_range(-0.42, 0.6)
			_tube(branches, root, end, 0.04 * (1.0 - tier / 16.0), 0.008)
			for spray in 6:
				var t := 0.2 + spray * 0.14
				var point := root.lerp(end, t)
				for side in [-1, 1]:
					var direction: Vector3 = (radial * 0.55 + across * side * 0.85 + Vector3.UP * random.randf_range(0.05, 0.4)).normalized()
					var size := (0.45 + reach * 0.22) * (1.0 - t * 0.45)
					_sprig(leaves, point, direction, size, Color(0.76, 0.89, 0.64) * random.randf_range(0.8, 1.05))
	for i in 7:
		_sprig(leaves, Vector3(0, 9.4, 0), Vector3(cos(i), 2.2, sin(i)).normalized(), 0.85, Color(0.7, 0.83, 0.57))
	var bark := StandardMaterial3D.new()
	bark.resource_name = "conifer_bark"
	bark.albedo_texture = load("res://assets/models/polyhaven/fir_sapling/fir_sapling_branches_diff_2k.jpg")
	bark.albedo_color = Color(0.62, 0.56, 0.48)
	bark.roughness = 0.95
	var branch_mat := bark.duplicate()
	branch_mat.resource_name = "canopy_branches"
	var foliage := ShaderMaterial.new()
	foliage.resource_name = "conifer_leaves"
	foliage.shader = load("res://assets/shaders/valley_needles.gdshader")
	foliage.set_shader_parameter("albedo_texture", load("res://assets/textures/scenic_valley/pine_twig_diff.jpg"))
	foliage.set_shader_parameter("alpha_texture", load("res://assets/textures/scenic_valley/pine_twig_alpha.png"))
	trunk.set_material(bark)
	branches.set_material(branch_mat)
	leaves.set_material(foliage)
	return [trunk.commit(), branches.commit(), leaves.commit()]
