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
	var model: Node3D = _gun.get("_model")
	print("gun pos=", _gun.position, " rot=", _gun.rotation_degrees)
	print("model pos=", model.position, " rot=", model.rotation_degrees, " scale=", model.scale)
	print("gun children:")
	for c in _gun.get_children():
		print("  ", c.name, " ", c.get_class())
	for pair in [["start", 0.0], ["removing", 0.2], ["hold", 0.45], ["inserting", 0.8], ["done", 1.0]]:
		var tag: String = pair[0]
		var prog: float = pair[1]
		_gun.set("_reload_t", 1.5 * (1.0 - prog))
		_gun.call("_process", 0.016)
		print(tag, " prog=", prog, " mag_y=", mag.position.y if mag else "?", " rot_x=", mag.rotation.x if mag else "?")
		if tag == "hold":
			var mag_mi := mag.get_child(0) as MeshInstance3D
			var aabb := (mag_mi.mesh as ArrayMesh).get_aabb()
			var xf := mag.global_transform
			var corners := [
				Vector3(aabb.position.x, aabb.position.y, aabb.position.z),
				Vector3(aabb.end.x, aabb.position.y, aabb.position.z),
				Vector3(aabb.position.x, aabb.end.y, aabb.position.z),
				Vector3(aabb.position.x, aabb.position.y, aabb.end.z),
				Vector3(aabb.end.x, aabb.end.y, aabb.end.z),
			]
			for c in corners:
				var wp: Vector3 = xf * c
				print("  mag corner world=", wp)
	quit(0)
	return false
