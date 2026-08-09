extends SceneTree
## 直接验证：GLB 枪口(+X) 在 rotation.y = ±90° 下的世界方向
## 运行：& $godot --headless --path 'E:\3d\3-dfps' --script res://tests/verify_akm_rotation.gd

func _process(_delta: float) -> bool:
	var glb: PackedScene = load("res://assets/models/akm_trellis.glb")
	for deg in [90.0, -90.0]:
		var n := glb.instantiate()
		root.add_child(n)
		n.rotation_degrees.y = deg
		# 枪口在模型局部 +X（0.5, 0, 0），转成世界方向
		var dir: Vector3 = n.global_transform.basis * Vector3(1, 0, 0)
		var label := "前(-Z)" if dir.z < 0.0 else "后(+Z/镜头)"
		print("rot_y=", deg, " -> muzzle_dir=", dir, " => ", label)
		n.queue_free()
	quit(0)
	return false
