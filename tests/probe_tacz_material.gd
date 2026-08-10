extends SceneTree
var _f := 0
func _process(_d) -> bool:
	_f += 1
	if _f == 1:
		var body: PackedScene = load("res://assets/models/tacz_ak47/ak47_additive.glb")
		var b := body.instantiate()
		root.add_child(b)
		var mi := b.find_child("gun", true, false) as MeshInstance3D
		var mesh: Mesh = mi.mesh
		var mat: Material = mesh.surface_get_material(0)
		print("mat class:", mat.get_class() if mat else "null")
		if mat is StandardMaterial3D:
			var sm := mat as StandardMaterial3D
			print("transparency:", sm.transparency, " cull:", sm.cull_mode, " shading:", sm.shading_mode)
			print("albedo_tex:", sm.albedo_texture)
		quit(0)
		return false
	return false
