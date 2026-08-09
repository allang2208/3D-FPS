# 换弹中段渲染（真弹匣滑出验证）：$env:RELOAD_PROG 0..1，默认 0.5（弹匣完全卸下）
extends SceneTree
var _f := 0
var _gun: Node3D

func _process(_d) -> bool:
	_f += 1
	if _f == 1:
		var env := Environment.new()
		env.background_mode = Environment.BG_COLOR
		env.background_color = Color(0.13, 0.13, 0.15)
		env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
		env.ambient_light_color = Color(0.65, 0.65, 0.68)
		env.ambient_light_energy = 1.0
		var we := WorldEnvironment.new()
		we.environment = env
		root.add_child(we)
		var light := DirectionalLight3D.new()
		light.rotation_degrees = Vector3(-45, 140, 0)
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
	if _f == 3:
		var prog := 0.5
		var p := OS.get_environment("RELOAD_PROG")
		if p != "":
			prog = clampf(float(p), 0.0, 1.0)
		_gun.set("_reload_t", _gun.get("data").reload_time * (1.0 - prog))
		_gun.set("_ads", false)
		_gun.set("_ads_factor", 0.0)
	if _f == 15:
		var img := root.get_viewport().get_texture().get_image()
		if img != null and img.get_width() > 0:
			img.save_png("user://gun_reload_mag_out.png")
			print("SAVED ", ProjectSettings.globalize_path("user://gun_reload_mag_out.png"))
		quit(0)
		return false
	return false
