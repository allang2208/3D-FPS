extends RefCounted

static func create() -> ShaderMaterial:
	var material := ShaderMaterial.new()
	# Same volumetric stone as the hub: continuous across rounded faces, no UV seams.
	material.shader = preload("res://assets/environment/sky_base/marble.gdshader")
	material.set_shader_parameter("stone_color", Color(0.64, 0.67, 0.66))
	material.set_shader_parameter("vein_color", Color(0.25, 0.31, 0.36))
	material.set_shader_parameter("stone_roughness", 0.30)
	material.set_shader_parameter("individual_slab", true)
	material.set_shader_parameter("slab_pattern_scale", 2.8)
	material.set_shader_parameter("vein_strength", 0.55)
	material.set_shader_parameter("fine_slab_detail", true)
	return material
