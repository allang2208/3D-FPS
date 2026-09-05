extends RefCounted

## Six fixed silhouettes; both LODs consume exactly the same random sequence.
const VARIANTS := 6

static func center(y: float, variant: int) -> Vector3:
	var t := y / 10.0
	return Vector3(sin(t * 2.3) * t * 0.32 + t * t * 0.12 * cos(variant), y,
		sin(t * 3.1 + variant) * t * 0.22)

static func tube(st: SurfaceTool, start: Vector3, end: Vector3, radius: float, tip: float, v_start: float = 0) -> void:
	var axis := (end - start).normalized()
	var right := axis.cross(Vector3.FORWARD).normalized()
	var forward := right.cross(axis).normalized()
	for i in 7:
		var a := right * cos(TAU * i / 7) + forward * sin(TAU * i / 7)
		var b := right * cos(TAU * (i + 1) / 7) + forward * sin(TAU * (i + 1) / 7)
		var points := [start + a * radius, end + a * tip, start + b * radius, end + b * tip]
		for index in [0, 1, 2, 2, 1, 3]:
			st.set_normal(a if index < 2 else b)
			st.set_uv(Vector2((i + (1 if index >= 2 else 0)) / 7.0, v_start + (start.distance_to(end) if index % 2 else 0)))
			st.add_vertex(points[index])

static func sprig(st: SurfaceTool, origin: Vector3, along: Vector3, size: float, tint: Color, roll: float) -> void:
	var side := along.cross(Vector3.UP).normalized().rotated(along, roll)
	for crossed in 2:
		var across := side.rotated(along, crossed * 1.22)
		# Fold the card along its length rather than presenting two flat rectangles.
		var normal := along.cross(across).normalized()
		var points := [origin - across * size * 0.25, origin + across * size * 0.25,
			origin + along * size * 0.53 + normal * size * 0.09 - across * size * 0.25,
			origin + along * size * 0.53 + normal * size * 0.09 + across * size * 0.25,
			origin + along * size - across * size * 0.20, origin + along * size + across * size * 0.20]
		for index in [0, 2, 1, 1, 2, 3, 2, 4, 3, 3, 4, 5]:
			st.set_color(tint)
			st.set_uv(Vector2(0.006 if index % 2 == 0 else 0.246, [0.443, 0.214, 0.01][index / 2]))
			st.set_normal((normal + Vector3.UP * 0.7).normalized())
			st.add_vertex(points[index])

static func make_meshes(variant: int, simplified: bool = false) -> Array[ArrayMesh]:
	var rng := RandomNumberGenerator.new()
	rng.seed = 57043 + variant * 971
	var trunk := SurfaceTool.new()
	var branches := SurfaceTool.new()
	var leaves := SurfaceTool.new()
	for st in [trunk, branches, leaves]:
		st.begin(Mesh.PRIMITIVE_TRIANGLES)
	# Horizontal shared rings keep the curved trunk watertight and its base flat.
	for section in 20:
		for side in 10:
			for corner in [0, 2, 1, 1, 2, 3]:
				var y: float = (section + corner / 2) * 0.5
				var angle: float = TAU * (side + corner % 2) / 10.0
				var radius := lerpf(0.22, 0.009, y / 10.0) + 0.075 * exp(-y * 4)
				var radial := Vector3(cos(angle), 0, sin(angle))
				radius *= 1.0 + 0.055 * sin(angle * 3 + variant)
				trunk.set_normal(radial)
				trunk.set_uv(Vector2((side + corner % 2) / 10.0, y * 0.65))
				trunk.add_vertex(center(y, variant) + radial * radius)
	var crown_start: float = [2.1, 3.0, 2.6, 2.4, 3.3, 2.8][variant]
	var width: float = [0.86, 1.08, 0.95, 1.13, 0.82, 1.0][variant]
	for tier in 11:
		var t := tier / 10.0
		var y := lerpf(crown_start, 9.25, t) + rng.randf_range(-0.25, 0.25)
		var reach := (2.7 * pow(1.0 - t, 0.65) + 0.12) * width
		var count := rng.randi_range(4, 6)
		var phase := tier * 2.399963 + variant
		for branch in count:
			var angle := phase + branch * TAU / count + rng.randf_range(-0.4, 0.4)
			var radial := Vector3(cos(angle), 0, sin(angle))
			var across := Vector3(-radial.z, 0, radial.x)
			var length := reach * rng.randf_range(0.65, 1.17) * (1 + 0.16 * cos(angle - variant))
			var base_y := y + rng.randf_range(-0.38, 0.38)
			var root := center(base_y, variant)
			var bend := root + radial * length * 0.48 + Vector3.UP * lerpf(-0.25, 0.26, t)
			var end := root + radial * length + Vector3.UP * rng.randf_range(-0.1, 0.62)
			var dead := tier < 2 and branch == variant % count
			if not simplified:
				tube(branches, root, bend, 0.035 * (1 - t * 0.7), 0.018)
				tube(branches, bend, end, 0.018, 0.003, root.distance_to(bend))
			for spray in 4:
				var f := 0.22 + spray * 0.23
				var point := root.lerp(bend, f * 2) if f < 0.5 else bend.lerp(end, (f - 0.5) * 2)
				for sign_value in [-1, 1]:
					var direction: Vector3 = (radial * rng.randf_range(0.45, 0.85) + across * sign_value * 0.7 + Vector3.UP * rng.randf_range(-0.15, 0.45)).normalized()
					var size := (0.42 + reach * 0.25) * (1 - f * 0.4) * rng.randf_range(0.8, 1.18)
					var roll := rng.randf_range(-0.5, 0.5)
					var tint := Color(0.69, 0.83, 0.57).lerp(Color(0.86, 0.94, 0.68), f * 0.32 + t * 0.18) * rng.randf_range(0.86, 1.04)
					if not dead and (not simplified or spray % 2 == 1):
						sprig(leaves, point, direction, size * (1.4 if simplified else 1.0), tint, roll)
	for i in 5:
		var direction := Vector3(cos(i * 2.4), 1.5, sin(i * 2.4)).normalized()
		sprig(leaves, center(9.4 + i * 0.05, variant), direction, 0.65, Color(0.8, 0.9, 0.65), i * 0.3)
	var bark := StandardMaterial3D.new()
	bark.resource_name = "conifer_bark"
	bark.albedo_texture = load("res://assets/models/polyhaven/fir_sapling/fir_sapling_branches_diff_2k.jpg")
	bark.albedo_color = Color(0.72, 0.65, 0.55)
	bark.roughness = 0.95
	bark.normal_enabled = not simplified
	bark.normal_texture = load("res://assets/models/polyhaven/fir_sapling/fir_sapling_branches_nor_gl_2k.jpg")
	bark.normal_scale = 0.55
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
	trunk.generate_tangents()
	if simplified:
		return [trunk.commit(), leaves.commit()]
	branches.generate_tangents()
	return [trunk.commit(), branches.commit(), leaves.commit()]
