extends SceneTree
## 验证：体素枪独立弹匣在换弹时下滑
## 运行： $godot --headless --path 'E:\3d\3-dfps' --script res://tests/probe_mag_reload.gd

var _frames := 0
var _gun: Node3D

func _process(_delta: float) -> bool:
	_frames += 1
	if _frames == 1:
		var cam := Camera3D.new()
		root.add_child(cam)
		var gun := Node3D.new()
		gun.set_script(load("res://scripts/gun.gd"))
		cam.add_child(gun)
		_gun = gun
	if _frames < 3:
		return false
	var mag: Node3D = _gun.get("_mag")
	print("mag=", mag.name if mag else "null", " parent=", mag.get_parent().name if mag and mag.get_parent() else "-")
	print("mag_base_y=", _gun.get("_mag_base_y"), " slide=", _gun.get("_mag_slide"))
	print("pos0=", mag.position if mag else "?")
	_gun.set("_reload_t", 0.75)
	_gun.call("_process", 0.016)
	print("pos_mid=", mag.position if mag else "?")
	_gun.set("_reload_t", 0.2)
	_gun.call("_process", 0.016)
	print("pos_late=", mag.position if mag else "?")
	quit(0)
	return false
