extends SceneTree
## 孤立渲染 IK 手臂（无枪、亮材质），确认手臂本体形状/位置是否正确
## 运行：$godot --rendering-driver opengl3 --path 'E:\3d\3-dfps' --script res://tests/render_arm_isolated.gd

var _frames := 0
var _arm: Node3D
var _target: Node3D

func _process(_delta: float) -> bool:
	_frames += 1
	if _frames == 1:
		var env := Environment.new()
		env.background_mode = Environment.BG_COLOR
		env.background_color = Color(0.55, 0.55, 0.58)
		env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
		env.ambient_light_color = Color(1, 1, 1)
		env.ambient_light_energy = 0.8
		var we := WorldEnvironment.new()
		we.environment = env
		root.add_child(we)
		var cam := Camera3D.new()
		cam.name = "Cam"
		cam.fov = 75.0
		root.add_child(cam)
		cam.make_current()
		var holder := Node3D.new()
		holder.position = Vector3(0.28, -0.15, -0.5)
		root.add_child(holder)
		var arm := Node3D.new()
		arm.name = "LeftArm"
		arm.set_script(load("res://scripts/viewmodel_arms.gd"))
		holder.add_child(arm)
		_arm = arm
		_target = arm.get_node("HandTarget") as Node3D
		# 亮材质覆盖，方便像素识别
		var mi := arm.get_node("ArmMesh") as MeshInstance3D
		print("mesh surfaces=", mi.mesh.get_surface_count(), " aabb=", mi.mesh.get_aabb(),
				" tri_count=", _tri_count(mi.mesh))
		var m0 := StandardMaterial3D.new()
		m0.albedo_color = Color(0.95, 0.30, 0.20)
		m0.roughness = 0.5
		var m1 := StandardMaterial3D.new()
		m1.albedo_color = Color(0.20, 0.95, 0.30)
		m1.roughness = 0.5
		mi.mesh.surface_set_material(0, m0)
		mi.mesh.surface_set_material(1, m1)
	if _frames == 12:
		_save("user://iso_rest.png")
		_target.position = Vector3(-0.06, -0.19, -0.04)  # 模拟换弹插回阶段的目标
	if _frames == 30:
		_save("user://iso_reach.png")
		var mi2 := _arm.get_node("ArmMesh") as MeshInstance3D
		mi2.skin = null
		mi2.skeleton = NodePath("")
	if _frames == 38:
		_save("user://iso_noskin.png")
		quit(0)
		return false
	return false

func _tri_count(mesh: Mesh) -> int:
	var total := 0
	for s in mesh.get_surface_count():
		var arr := mesh.surface_get_arrays(s)
		if arr.size() > 0 and arr[Mesh.ARRAY_INDEX] != null:
			total += (arr[Mesh.ARRAY_INDEX] as PackedInt32Array).size() / 3
	return total

func _save(path: String) -> void:
	var img := root.get_viewport().get_texture().get_image()
	if img == null or img.get_width() == 0:
		print("EMPTY at ", path)
		return
	img.save_png(path)
	print("SAVED ", ProjectSettings.globalize_path(path))
