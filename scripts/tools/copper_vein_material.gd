extends RefCounted
static func create(mesh: Mesh=null) -> ShaderMaterial:
	var material:=preload("res://scripts/tools/iron_vein_material.gd").create(mesh)
	material.set_shader_parameter("rock_color",load("res://assets/environment/copper_vein_v1/copper_albedo.png"))
	material.set_shader_parameter("mineral_metallic",0.06)
	return material
