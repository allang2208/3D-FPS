# 通用 GLB 模型渲染验证：$env:DL_GLB 指定 res:// 路径，$env:DL_TAG 指定文件名后缀
# 自动按 AABB 取景，输出侧视 + 45° 视图（带光照）
extends SceneTree
var _f := 0
var _cam: Camera3D
var _node: Node3D
var _center: Vector3
var _radius: float
var _tag := "dl"

func _process(_d) -> bool:
	_f += 1
	if _f == 1:
		var path := OS.get_environment("DL_GLB")
		if path == "":
			quit(1)
			return false
		var tag := OS.get_environment("DL_TAG")
		if tag != "":
			_tag = tag
		var packed: PackedScene = load(path)
		if packed == null:
			print("LOAD FAILED ", path)
			quit(1)
			return false
		_node = packed.instantiate()
		root.add_child(_node)
		var aabb := _collect_aabb(_node)
		_center = aabb.get_center()
		_radius = maxf(aabb.size.x, maxf(aabb.size.y, aabb.size.z)) * 0.65
		_node.position = -_center
		print("loaded ", path, " size=", aabb.size, " center=", _center, " radius=", _radius)
		var env := Environment.new()
		env.background_mode = Environment.BG_COLOR
		env.background_color = Color(0.14, 0.14, 0.16)
		env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
		env.ambient_light_color = Color(0.65, 0.65, 0.68)
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
		_cam.position = Vector3(0, -_radius * 0.15, _radius / tan(deg_to_rad(19.0)) * 1.25)
		_cam.look_at(Vector3.ZERO, Vector3.UP)
	if _f == 15:
		_save("user://dl_side_" + _tag + ".png")
		_cam.position = Vector3(_radius, _radius * 0.45, _radius / tan(deg_to_rad(19.0)) * 1.25)
		_cam.look_at(Vector3.ZERO, Vector3.UP)
	if _f == 30:
		_save("user://dl_34_" + _tag + ".png")
		quit(0)
		return false
	return false

func _collect_aabb(node: Node) -> AABB:
	var aabb := AABB()
	for child in node.get_children():
		var ca: AABB = _collect_aabb(child)
		if ca.size.length() > 0.0:
			if aabb.size.length() == 0.0:
				aabb = ca
			else:
				aabb = aabb.merge(ca)
	if node is VisualInstance3D:
		var vi := node as VisualInstance3D
		var ta0: AABB = vi.get_aabb()
		var xf: Transform3D = vi.global_transform
		var lo: Vector3 = xf * ta0.position
		var hi: Vector3 = lo
		for corner in [
			ta0.position + Vector3(ta0.size.x, 0, 0),
			ta0.position + Vector3(0, ta0.size.y, 0),
			ta0.position + Vector3(0, 0, ta0.size.z),
			ta0.position + Vector3(ta0.size.x, ta0.size.y, 0),
			ta0.position + Vector3(ta0.size.x, 0, ta0.size.z),
			ta0.position + Vector3(0, ta0.size.y, ta0.size.z),
			ta0.position + ta0.size,
		]:
			var p: Vector3 = xf * corner
			lo = lo.min(p)
			hi = hi.max(p)
		var ta: AABB = AABB(lo, hi - lo)
		if ta.size.length() > 0.0:
			if aabb.size.length() == 0.0:
				aabb = ta
			else:
				aabb = aabb.merge(ta)
	return aabb

func _save(p: String) -> void:
	var img := root.get_viewport().get_texture().get_image()
	if img != null and img.get_width() > 0:
		img.save_png(p)
		print("SAVED ", p)
	else:
		print("NO IMAGE ", p)
