extends SceneTree
var _f := 0
func _process(_d) -> bool:
	_f += 1
	if _f == 1:
		var scene: PackedScene = load("res://assets/models/tacz_ak47/ak47_additive.glb")
		var inst := scene.instantiate()
		root.add_child(inst)
		_dump(inst, 0)
		quit(0)
		return false
	return false

func _dump(n: Node, depth: int) -> void:
	var t := ""
	if n is Node3D:
		var n3 := n as Node3D
		t = " pos=%s rot=%s scale=%s" % [n3.position, n3.rotation_degrees, n3.scale]
	print("  ".repeat(depth), n.get_class(), " | ", n.name, t)
	if n is Skeleton3D:
		var sk := n as Skeleton3D
		for i in sk.get_bone_count():
			var rest := sk.get_bone_rest(i)
			var gr := sk.get_bone_global_rest(i)
			print("  ".repeat(depth+1), "bone[", i, "] ", sk.get_bone_name(i),
				" rest.origin=", rest.origin, " rest.basis=", rest.basis,
				" global_rest.origin=", gr.origin)
	for c in n.get_children():
		_dump(c, depth + 1)
