extends RefCounted
static func create(mesh: Mesh=null) -> ShaderMaterial:
	var material:=ShaderMaterial.new()
	material.shader=preload("res://assets/environment/iron_vein_v1/iron.gdshader")
	material.set_shader_parameter("rock_color",load("res://assets/environment/iron_vein_v1/iron_albedo_v2.png"))
	if mesh!=null:
		var size:=mesh.get_aabb().size
		material.set_shader_parameter("pattern_scale",1.4/maxf(size.x,maxf(size.y,size.z)))
	return material
