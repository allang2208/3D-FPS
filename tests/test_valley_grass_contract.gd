extends SceneTree

var failures: Array[String] = []


func check(condition: bool, label: String) -> void:
	print("[grass-contract] ", "PASS " if condition else "FAIL ", label)
	if not condition:
		failures.append(label)


func _initialize() -> void:
	var foliage = load("res://scenes/scenic_foliage.gd")
	var near_mesh: ArrayMesh = foliage.grass_mesh()
	var middle_mesh: ArrayMesh = foliage.grass_mesh(2, 3)
	var far_mesh: ArrayMesh = foliage.grass_mesh(1, 2)
	check(near_mesh.surface_get_array_index_len(0) / 3 == 30, "near tuft remains 30 triangles")
	check(middle_mesh.surface_get_array_index_len(0) / 3 == 12, "middle tuft remains 12 triangles")
	check(far_mesh.surface_get_array_index_len(0) / 3 == 4, "far tuft remains 4 triangles")
	check(is_zero_approx(near_mesh.get_aabb().position.y), "near tuft roots remain at local ground")

	var process_shader: Shader = load("res://assets/shaders/valley_grass_process.gdshader")
	var grass_shader: Shader = load("res://assets/shaders/valley_grass.gdshader")
	var process_uniforms: Array[String] = []
	for entry in process_shader.get_shader_uniform_list():
		process_uniforms.append(entry.name)
	var grass_uniforms: Array[String] = []
	for entry in grass_shader.get_shader_uniform_list():
		grass_uniforms.append(entry.name)
	check("meadow_noise_scale" in process_uniforms, "process shader exposes deterministic meadow zoning")
	check("meadow_density_min" in process_uniforms and "meadow_density_max" in process_uniforms, "process shader exposes density budget")
	check("solid_exclusion" in process_uniforms, "process shader preserves hard obstacle exclusion")
	check("dry_grass_color" in grass_uniforms and "wet_grass_color" in grass_uniforms, "material exposes ecological palette")

	if failures.is_empty():
		print("[grass-contract] ALL PASS")
		quit(0)
	else:
		print("[grass-contract] failures=", failures)
		quit(1)
