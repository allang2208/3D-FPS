extends RefCounted
const ROOT := "res://assets/environment/sky_base/wood_generated_v3/"
static func create(upright := false) -> ShaderMaterial:
	var material := ShaderMaterial.new()
	material.shader=load(ROOT+"oak.gdshader")
	material.set_shader_parameter("wood_color",load(ROOT+"oak_albedo.png"))
	material.set_shader_parameter("upright",upright)
	return material
