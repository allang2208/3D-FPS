extends RefCounted

static func create_body() -> StandardMaterial3D:
	var material := StandardMaterial3D.new()
	material.albedo_color = Color("3b4850")
	material.metallic = .38
	material.roughness = .62
	return material

static func create_accent() -> StandardMaterial3D:
	var material := StandardMaterial3D.new()
	material.albedo_color = Color("9eb2bc")
	material.metallic = .72
	material.roughness = .30
	return material
