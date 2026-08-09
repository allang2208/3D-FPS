# 通用 OBJ/PLY Mesh 渲染验证：$env:MESH_PATH 指定 res:// 路径，$env:MESH_TAG 指定文件名后缀
# 保留模型自带材质，带光照输出侧视 + 45° 视图
extends SceneTree
var _f := 0
var _cam: Camera3D
var _mi: MeshInstance3D
var _tag := "mesh"

func _process(_d) -> bool:
	_f += 1
	if _f == 1:
		var path := OS.get_environment("MESH_PATH")
		if path == "":
			print("用法: 设置 MESH_PATH=res://assets/models/xxx.obj")
			quit(1)
			return false
		var tag := OS.get_environment("MESH_TAG")
		if tag != "":
			_tag = tag
		_mi = MeshInstance3D.new()
		_mi.mesh = load(path)
		if _mi.mesh == null:
			print("LOAD FAILED ", path)
			quit(1)
			return false
		var aabb: AABB = _mi.mesh.get_aabb()
		_mi.position = -aabb.get_center()
		root.add_child(_mi)
		var radius := maxf(aabb.size.x, maxf(aabb.size.y, aabb.size.z)) * 0.7
		print("loaded ", path, " size=", aabb.size, " tris=", _mi.mesh.get_faces().size() / 3)
		var env := Environment.new()
		env.background_mode = Environment.BG_COLOR
		env.background_color = Color(0.14, 0.14, 0.16)
		env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
		env.ambient_light_color = Color(0.7, 0.7, 0.72)
		env.ambient_light_energy = 1.0
		var we := WorldEnvironment.new()
		we.environment = env
		root.add_child(we)
		var light := DirectionalLight3D.new()
		light.rotation_degrees = Vector3(-40, 135, 0)
		root.add_child(light)
		_cam = Camera3D.new()
		_cam.fov = 38.0
		root.add_child(_cam)
		_cam.current = true
		_cam.position = Vector3(0, -radius * 0.15, radius / tan(deg_to_rad(19.0)) * 1.2)
		_cam.look_at(Vector3.ZERO, Vector3.UP)
	if _f == 15:
		_save("user://mesh_side_" + _tag + ".png")
		var radius2 := maxf(_mi.mesh.get_aabb().size.x, maxf(_mi.mesh.get_aabb().size.y, _mi.mesh.get_aabb().size.z)) * 0.7
		_cam.position = Vector3(radius2, radius2 * 0.45, radius2 / tan(deg_to_rad(19.0)) * 1.2)
		_cam.look_at(Vector3.ZERO, Vector3.UP)
	if _f == 30:
		_save("user://mesh_34_" + _tag + ".png")
		quit(0)
		return false
	return false

func _save(p: String) -> void:
	var img := root.get_viewport().get_texture().get_image()
	if img != null and img.get_width() > 0:
		img.save_png(p)
		print("SAVED ", p)
	else:
		print("NO IMAGE ", p)
