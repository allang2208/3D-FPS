extends RefCounted
static func create() -> ShaderMaterial:
	var material := ShaderMaterial.new()
	# Reuse the same rounded-surface projection and shallow relief pipeline.
	material.shader=load("res://assets/environment/sky_base/wood_generated_v3/oak.gdshader")
	material.set_shader_parameter("wood_color",load("res://assets/environment/sky_base/stone_voxel_v1/limestone_albedo.png"))
	material.set_shader_parameter("surface_tint",Vector3(.78,.81,.84))
	material.set_shader_parameter("roughness_range",Vector2(.88,.72))
	material.set_shader_parameter("pattern_scale",1.15)
	return material
