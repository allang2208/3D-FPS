extends SceneTree
## 渲染第一人称枪械视图：腰射 → 机瞄(ADS)，保存到 user://
## 运行： $godot --rendering-driver opengl3 --path 'E:\3d\3-dfps' --script res://tests/render_ads_view.gd

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
		var model_path := OS.get_environment("GUN_TEST_MODEL")
		if model_path != "":
			var wd := WeaponData.new()
			wd.model_scene = load(model_path)
			gun.set("data", wd)
		cam.add_child(gun)
		_gun = gun
	if _frames == 12:
		# 腰射
		_gun.set("_ads", false)
		_gun.set("_ads_factor", 0.0)
	if _frames == 15:
		_save("user://gun_hip.png")
		# 进入机瞄
		_gun.set("_ads", true)
		_gun.set("_ads_factor", 0.999)
	if _frames == 22:
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
