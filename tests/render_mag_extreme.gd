extends SceneTree
## 极端验证：弹匣额外下移 0.4m，确认独立弹匣是否真的渲染、能否分离
## 运行： $godot --rendering-driver opengl3 --path 'E:\3d\3-dfps' --script res://tests/render_mag_extreme.gd

var _frames := 0
var _gun: Node3D

func _process(_delta: float) -> bool:
	_frames += 1
	if _frames == 1:
		var cam := Camera3D.new()
		cam.name = "Cam"
		cam.fov = 75.0
		root.add_child(cam)
		cam.make_current()
		var gun := Node3D.new()
		gun.name = "Gun"
		gun.position = Vector3(0.28, -0.26, -0.5)
		gun.set_script(load("res://scripts/gun.gd"))
		cam.add_child(gun)
		_gun = gun
	if _frames == 5:
		_gun.set("_reload_t", 0.825)  # 保持阶段
		var mag: Node3D = _gun.get("_mag")
		mag.position = Vector3(-0.08, -0.45, 0.0)  # 明确下移，避免与枪体重叠
		print("mag_world=", mag.global_position)
		var cam3 := root.get_viewport().get_camera_3d()
		print("mag_screen=", cam3.unproject_position(mag.global_position))
	if _frames == 9:
		var img := root.get_viewport().get_texture().get_image()
		if img != null and img.get_width() > 0:
			var out := "user://gun_mag_extreme.png"
			img.save_png(out)
			print("SAVED ", ProjectSettings.globalize_path(out))
		quit(0)
		return false
	return false
