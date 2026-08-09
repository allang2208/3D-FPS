extends SceneTree
## 检查 AKM GLB 的结构：根节点尺寸/朝向/层级/材质数
## 运行：& $godot --headless --path 'E:\3d\3-dfps' --script res://tests/inspect_akm.gd

func _process(_delta: float) -> bool:
	var glb: PackedScene = load("res://assets/models/akm_trellis.glb")
	var root_node := glb.instantiate()
	root.add_child(root_node)
	await process_frame
	_process_node(root_node, 0)
	# 整体包围盒（根没有 get_aabb，取 mesh 子节点合并）
	var mesh_node := root_node.get_node("geometry_0") as MeshInstance3D
	if mesh_node:
		var aabb: AABB = mesh_node.get_aabb()
		print("MESH_AABB size=", aabb.size, " center=", aabb.get_center(), " pos=", aabb.position)
		# 绕 Y 旋转 90°（枪管 X → -Z）后的包围盒：数学变换，不依赖帧循环
		var p0 := aabb.position
		var p1 := aabb.end
		var min_z := minf(-p1.x, -p0.x)
		var max_z := maxf(-p1.x, -p0.x)
		print("MOUNTED size=(z)", aabb.size.z, ",", aabb.size.y, ",", aabb.size.x,
			" z_range=", min_z, "..", max_z, " 枪口(前)=", min_z, " 枪托(后)=", max_z)
	quit(0)
	return false

func _process_node(n: Node, depth: int) -> void:
	var indent := "  ".repeat(depth)
	var extra := ""
	if n is MeshInstance3D:
		var mi := n as MeshInstance3D
		if mi.mesh != null:
			extra = " mesh=%s aabb=%s" % [mi.mesh.get_name(), mi.get_aabb().size]
		if mi.material_override != null:
			extra += " mat_override=YES"
	print(indent, n.name, " pos=", n.position, " scale=", n.scale, " rot=", n.rotation, extra)
	for c in n.get_children():
		_process_node(c, depth + 1)
