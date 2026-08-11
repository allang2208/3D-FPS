extends SceneTree
## 渲染第一人称 IK 手臂：腰射 → 换弹各阶段 → ADS，保存到 user://
## 运行： $godot --rendering-driver opengl3 --path 'E:\3d\3-dfps' --script res://tests/render_arm_reload.gd

var _frames := 0
var _gun: Node3D

func _process(_delta: float) -> bool:
	_frames += 1
	if _frames == 1:
		var env := Environment.new()
		env.background_mode = Environment.BG_COLOR
		env.background_color = Color(0.13, 0.13, 0.15)
		env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
		env.ambient_light_color = Color(0.9, 0.9, 0.95)
		env.ambient_light_energy = 2.2
		var we := WorldEnvironment.new()
		we.environment = env
		root.add_child(we)
		var light := DirectionalLight3D.new()
		light.rotation_degrees = Vector3(-35, 130, 0)
		light.light_energy = 2.4
		root.add_child(light)
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
	if _frames == 12:
		_save("user://arm_hip.png")
		_gun.call("_start_reload")
	if _frames == 20:
		_save("user://arm_reload_pullout.png")
	if _frames == 36:
		_save("user://arm_reload_magout.png")
	if _frames == 60:
		_save("user://arm_reload_hold.png")
	if _frames == 92:
		_save("user://arm_reload_insert.png")
	if _frames == 112:
		_gun.set("_ads", true)
		_gun.set("_ads_factor", 0.999)
	if _frames == 118:
		_save("user://arm_ads.png")
		quit(0)
		return false
	return false

func _save(path: String) -> void:
	var img := root.get_viewport().get_texture().get_image()
	if img == null or img.get_width() == 0:
		print("EMPTY at ", path)
		return
	img.save_png(path)
	print("SAVED ", ProjectSettings.globalize_path(path))
