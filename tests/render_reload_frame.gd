extends SceneTree
## 渲染换弹中帧（弹匣滑出）预览
## 运行： $godot --rendering-driver opengl3 --path 'E:\3d\3-dfps' --script res://tests/render_reload_frame.gd

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
		gun.set_physics_process(false)  # 固定换弹进度，避免物理帧衰减 _reload_t
		cam.add_child(gun)
		_gun = gun
	if _frames == 8:
		_gun.set("_reload_t", 1.5 * 0.8)  # prog 0.2：卸下中
	if _frames == 10:
		_save("user://gun_reload_removing.png")
		_gun.set("_reload_t", 1.5 * 0.55)  # prog 0.45：完全卸下保持
	if _frames == 12:
		_save("user://gun_reload_hold.png")
		_gun.set("_reload_t", 1.5 * 0.2)  # prog 0.8：插入中
	if _frames == 14:
		_save("user://gun_reload_inserting.png")
		quit(0)
		return false
	return false

func _save(path: String) -> void:
		var img := root.get_viewport().get_texture().get_image()
		if img != null and img.get_width() > 0:
			img.save_png(path)
			print("SAVED ", ProjectSettings.globalize_path(path))
