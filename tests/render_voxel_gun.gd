# 体素枪侧视图/45°视图渲染验证：$env:GUN_VOX_OBJ 指定 OBJ，$env:GUN_VOX_TAG 指定文件名后缀
extends SceneTree
var _f := 0
var _cam: Camera3D
var _mi: MeshInstance3D

func _process(_d) -> bool:
	_f += 1
	if _f == 1:
		var mesh_path := OS.get_environment("GUN_VOX_OBJ")
		if mesh_path == "":
			mesh_path = "res://assets/models/ak/akm_hand_built_v6.obj"
		_cam = Camera3D.new()
		_cam.fov = 40.0
		root.add_child(_cam)
		_cam.current = true
		_mi = MeshInstance3D.new()
		_mi.mesh = load(mesh_path)
		print("mesh loaded:", _mi.mesh != null, " aabb=", _mi.mesh.get_aabb() if _mi.mesh else "?")
		_mi.position = -(_mi.mesh.get_aabb().get_center())  # 居中（与 gun.gd 一致）
		var mat := StandardMaterial3D.new()
		mat.vertex_color_use_as_albedo = true
		mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
		_mi.material_override = mat
		root.add_child(_mi)
		# 侧视图：相机在 -Z 朝 +Z 看，枪长横贯画面
		_cam.position = Vector3(0, -0.02, -1.5)
		_cam.rotation_degrees.y = 180.0
	if _f == 15:
		var tag := OS.get_environment("GUN_VOX_TAG")
		if tag == "":
			tag = "v6"
		_save("user://handbuilt_side_" + tag + ".png")
		# 45° 前侧俯视图
		_cam.position = Vector3(1.0, 0.40, -1.60)
		_cam.look_at(Vector3.ZERO, Vector3.UP)
	if _f == 30:
		var tag2 := OS.get_environment("GUN_VOX_TAG")
		if tag2 == "":
			tag2 = "v6"
		_save("user://handbuilt_front34_" + tag2 + ".png")
		quit(0)
		return false
	return false

func _save(p: String) -> void:
	var img := root.get_viewport().get_texture().get_image()
	if img != null and img.get_width() > 0:
		img.save_png(p)
		print("SAVED ", p)
	else:
		print("NO IMAGE for ", p)
