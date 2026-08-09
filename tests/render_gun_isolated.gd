extends SceneTree
## 隔离渲染：相机 + 枪械节点，纯色背景，判定枪口朝向
## 运行：& $godot --rendering-driver opengl3 --path 'E:\3d\3-dfps' --script res://tests/render_gun_isolated.gd

var _frames := 0

func _process(_delta: float) -> bool:
	_frames += 1
	if _frames == 1:
		# 相机
		var cam := Camera3D.new()
		cam.name = "Cam"
		cam.fov = 75.0
		root.add_child(cam)
		cam.make_current()
		# 枪（模拟 main.gd 挂法：gun 是 cam 的子节点）
		var gun := Node3D.new()
		gun.name = "Gun"
		gun.position = Vector3(0.28, -0.26, -0.5)
		gun.set_script(load("res://scripts/gun.gd"))
		cam.add_child(gun)
	if _frames == 3:
		var gun := root.get_node("Cam/Gun")
		print("GUN children:")
		for c in gun.get_children():
			print("  ", c.name, " pos=", c.position, " rot=", c.rotation_degrees)
		var akm := gun.get_node_or_null("AkmModel")
		if akm:
			print("AKM rot_degrees=", akm.rotation_degrees, " children=", akm.get_child_count())
	if _frames < 15:
		return false
	var img := root.get_viewport().get_texture().get_image()
	if img == null or img.get_width() == 0:
		print("EMPTY")
		quit(0)
		return false
	img.save_png("user://gun_isolated.png")
	print("SAVED isolated")
	quit(0)
	return false
