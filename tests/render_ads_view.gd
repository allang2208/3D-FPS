extends SceneTree
## 渲染第一人称枪械视图：腰射 → 机瞄(ADS)，保存到 user://
## 运行： $godot --rendering-driver opengl3 --path 'E:\3d\3-dfps' --script res://tests/render_ads_view.gd

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
		var fill := DirectionalLight3D.new()
		fill.rotation_degrees = Vector3(20, -40, 0)
		fill.light_energy = 1.1
		fill.light_color = Color(0.75, 0.8, 0.95)
		root.add_child(fill)
		var cam := Camera3D.new()
		cam.name = "Cam"
		cam.fov = 75.0
		root.add_child(cam)
		cam.make_current()
		var gun := Node3D.new()
		gun.name = "Gun"
		gun.position = Vector3(0.28, -0.26, -0.5)
		gun.set_script(load("res://scripts/gun.gd"))
		var model_path := OS.get_environment("GUN_TEST_MODEL")
		if model_path != "":
			var wd := WeaponData.new()
			wd.model_scene = load(model_path)
			gun.set("data", wd)
		cam.add_child(gun)
		gun.set_process(false)
		gun.set_physics_process(false)
		_gun = gun
	if _frames == 12:
		# 腰射
		_gun.position = _gun.get("_view_pos")
		_gun.rotation = Vector3.ZERO
	if _frames == 15:
		_save("user://gun_hip.png")
		# 进入机瞄：直接摆到 ADS 完成姿态（ADS 姿态本身由 gun 数学校准保证 rear/front 投影居中）
		_gun.position = _gun.get("_ads_pos")
		_gun.rotation = _gun.get("_ads_rot")
	if _frames == 45:
		var cam := root.get_node("Cam") as Camera3D
		var rear: Vector3 = _gun.get("_sight_rear")
		print("F45 gun_pos=", _gun.position, " rot=", _gun.rotation, " ads_factor=", _gun.get("_ads_factor"))
		print("F45 rear_world=", _gun.global_transform * rear,
				" screen=", cam.unproject_position(_gun.global_transform * rear))
		var front: Vector3 = _gun.get("_sight_front")
		print("F45 front_world=", _gun.global_transform * front,
				" screen=", cam.unproject_position(_gun.global_transform * front))
		_save("user://gun_ads.png")
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
