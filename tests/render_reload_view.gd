extends SceneTree
## 换弹渲染：亮背景量化弹匣是否飞出画面（magout/hold 帧弹匣应无暗像素或贴边）
## 运行：$godot --rendering-driver opengl3 --path 'E:\3d\3-dfps' --script res://tests/render_reload_view.gd

var _frames := 0
var _gun: Node3D

func _process(_delta: float) -> bool:
	_frames += 1
	if _frames == 1:
		Engine.max_fps = 60
		var env := Environment.new()
		env.background_mode = Environment.BG_COLOR
		env.background_color = Color(0.55, 0.55, 0.58)
		env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
		env.ambient_light_color = Color(1, 1, 1)
		env.ambient_light_energy = 0.45
		var we := WorldEnvironment.new()
		we.environment = env
		root.add_child(we)
		var light := DirectionalLight3D.new()
		light.rotation_degrees = Vector3(-40, 120, 0)
		light.light_energy = 0.9
		root.add_child(light)
		var cam := Camera3D.new()
		cam.name = "Cam"
		cam.fov = 75.0
		root.add_child(cam)
		cam.make_current()
		var gun := Node3D.new()
		gun.name = "Gun"
		gun.set_script(load("res://scripts/gun.gd"))
		cam.add_child(gun)
		_gun = gun
		# 弹匣染红，便于像素追踪飞出/飞回轨迹
		var mag_mi := gun.get_node("AkmModel/Magazine").get_child(0) as MeshInstance3D
		var red := StandardMaterial3D.new()
		red.albedo_color = Color(1.0, 0.18, 0.12)
		red.roughness = 0.4
		mag_mi.material_override = red
	if _frames == 12:
		_save("user://rl_hip.png")
		_gun.call("_start_reload")
	if _frames == 26:
		_save("user://rl_pullout.png")
	if _frames == 42:
		_save("user://rl_magout.png")
	if _frames == 75:
		_save("user://rl_hold.png")
	if _frames == 105:
		_save("user://rl_insert.png")
	if _frames == 120:
		quit(0)
		return false
	return false

func _save(path: String) -> void:
	var mag: Node3D = _gun.get("_mag")
	print("  [save ", path, "] reload_t=", _gun.get("_reload_t"),
			" mag_pos=", mag.position if mag != null else Vector3.ZERO)
	var img := root.get_viewport().get_texture().get_image()
	if img == null or img.get_width() == 0:
		print("EMPTY at ", path)
		return
	img.save_png(path)
	print("SAVED ", ProjectSettings.globalize_path(path))
