extends RefCounted
static func create(kind: String, mesh: Mesh=null) -> ShaderMaterial:
	assert(kind in ["silver","gold"])
	var material:=preload("res://scripts/tools/iron_vein_material.gd").create(mesh)
	material.set_shader_parameter("rock_color",load("res://assets/environment/%s_vein_v1/%s_albedo.png" % [kind,kind]))
	material.set_shader_parameter("mineral_mode",1 if kind=="silver" else 2)
	material.set_shader_parameter("mineral_metallic",0.95)
	return material
