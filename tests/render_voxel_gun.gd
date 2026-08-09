# 体素枪侧视图/45°视图渲染验证：$env:GUN_VOX_OBJ 指定 OBJ，$env:GUN_VOX_TAG 指定文件名后缀
extends SceneTree
var _f := 0
var _cam: Camera3D
var _mi: MeshInstance3D
var _tag := "v6"

func _process(_d) -> bool:
	_f += 1
	if _f == 1:
		var mesh_path := OS.get_environment("GUN_VOX_OBJ")
		if mesh_path == "":
			print("用法: 设置 GUN_VOX_OBJ=res://assets/models/ak/xxx.obj（由 voxel_ak_builder 生成）")
			quit(1)
			return false
		var tag := OS.get_environment("GUN_VOX_TAG")
		if tag != "":
			_tag = tag
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
		_save("user://handbuilt_side_" + _tag + ".png")
		# 45° 前侧俯视图
		_cam.position = Vector3(1.0, 0.40, -1.60)
		_cam.look_at(Vector3.ZERO, Vector3.UP)
	if _f == 30:
		_save("user://handbuilt_front34_" + _tag + ".png")
		# 带光照的 Flat 渲染（侧视图），看轮廓立体感
		var env := Environment.new()
		env.background_mode = Environment.BG_COLOR
		env.background_color = Color(0.12, 0.12, 0.14)
		env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
		env.ambient_light_color = Color(0.55, 0.55, 0.58)
		env.ambient_light_energy = 1.0
		var we := WorldEnvironment.new()
		we.environment = env
		root.add_child(we)
		var light := DirectionalLight3D.new()
		light.rotation_degrees = Vector3(-45, 140, 0)
		root.add_child(light)
		var mat := StandardMaterial3D.new()
		mat.vertex_color_use_as_albedo = true
		_mi.material_override = mat
		_cam.position = Vector3(0, -0.02, -1.5)
		_cam.rotation_degrees.y = 180.0
	if _f == 45:
		_save("user://handbuilt_side_lit_" + _tag + ".png")
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
