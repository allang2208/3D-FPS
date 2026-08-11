extends SceneTree
## 计算 mag_offset = 弹匣网格中心 − 枪身网格中心（二者都被 gun.gd 居中到原点）
## 运行：$godot --headless --path 'E:\3d\3-dfps' --script res://tests/probe_mag_offset.gd

func _init() -> void:
	_calc("lowpoly", "res://assets/models/ak/lowpoly_akm/lowpoly_body.tres",
			"res://assets/models/ak/lowpoly_akm/lowpoly_mag.tres")
	_calc("akm_glb", "res://assets/models/ak/akm_glb/akm_body.tres",
			"res://assets/models/ak/akm_glb/akm_mag.tres")
	quit(0)

func _calc(tag: String, body_path: String, mag_path: String) -> void:
	var body: Mesh = load(body_path)
	var mag: Mesh = load(mag_path)
	if body == null or mag == null:
		print(tag, " LOAD FAIL")
		return
	var bc: Vector3 = body.get_aabb().get_center()
	var mc: Vector3 = mag.get_aabb().get_center()
	var off := mc - bc
	print(tag, " body_center=", bc, " mag_center=", mc, " -> mag_offset=", off)
