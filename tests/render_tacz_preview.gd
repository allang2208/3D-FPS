extends SceneTree
## TACZ 模型转换验证：多角度渲染 GLB + 播放动画。
## 用法：
##   $env:GUN_GLB='res://assets/models/tacz_ak47/ak47_replace.glb'
##   $env:ANIM_NAME='static_idle'
##   $godot --rendering-driver opengl3 --path 'E:\3d\3-dfps' --script res://tests/render_tacz_preview.gd

var _frames := 0
var _gun: Node3D
var _anim_player: AnimationPlayer
var _target := Vector3.ZERO
var _views := [
	["tacz_idle", Vector3(0.0, 0.08, 1.05)],
	["tacz_side", Vector3(1.25, 0.28, 0.0)],
	["tacz_front34", Vector3(0.75, 0.35, 0.85)],
]
var _shot := 0

func _process(_delta: float) -> bool:
	_frames += 1
	if _frames == 1:
		_setup_env()
		_gun = _instantiate_gun()
		_anim_player = _gun.get_node_or_null("AnimationPlayer")
		if _anim_player:
			print("ANIMS: ", _anim_player.get_animation_list())
		var cam := Camera3D.new()
		cam.name = "Cam"
		cam.fov = 75.0
		root.add_child(cam)
		cam.make_current()
	if _frames == 2 and _anim_player:
		var anim_name := OS.get_environment("ANIM_NAME")
		if anim_name == "":
			anim_name = "static_idle"
		if anim_name == "__none__":
			print("NO ANIMATION (rest pose)")
		elif _anim_player.has_animation(anim_name):
			_anim_player.play(anim_name)
			_anim_player.seek(OS.get_environment("ANIM_TIME").to_float() if OS.get_environment("ANIM_TIME") != "" else 0.0, true)
			_anim_player.speed_scale = 0.0
			print("PLAYED ", anim_name)
	if _frames == 8:
		_apply_view(0)
	if _frames == 16:
		_save_shot(0)
	if _frames == 24:
		_apply_view(1)
	if _frames == 32:
		_save_shot(1)
	if _frames == 40:
		_apply_view(2)
	if _frames == 48:
		_save_shot(2)
		quit(0)
		return false
	return false

func _setup_env() -> void:
	var env := Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color(0.12, 0.12, 0.14)
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color(0.8, 0.8, 0.85)
	env.ambient_light_energy = 1.2
	var we := WorldEnvironment.new()
	we.environment = env
	root.add_child(we)
	var light := DirectionalLight3D.new()
	light.rotation_degrees = Vector3(-35, 130, 0)
	light.light_energy = 1.6
	root.add_child(light)

func _instantiate_gun() -> Node3D:
	var glb := OS.get_environment("GUN_GLB")
	if glb == "":
		glb = "res://assets/models/tacz_ak47/ak47_replace.glb"
	var scene: PackedScene = load(glb)
	var inst: Node3D = scene.instantiate()
	root.add_child(inst)
	var bounds := _aabb_of(inst)
	print("AABB min=", bounds.position, " max=", bounds.end, " size=", bounds.size)
	_target = bounds.get_center()
	print("CENTER=", _target)
	return inst

func _aabb_of(node: Node3D) -> AABB:
	var total := AABB()
	var first := true
	for mi in node.find_children("*", "MeshInstance3D", true, false):
		var mesh: Mesh = mi.mesh
		if mesh == null:
			continue
		var bb: AABB = mesh.get_aabb().grow(0.001)
		bb = mi.global_transform * bb
		if first:
			total = bb
			first = false
		else:
			total = total.merge(bb)
	return total

func _apply_view(idx: int) -> void:
	var cam := root.get_node("Cam") as Camera3D
	var v: Array = _views[idx]
	cam.position = v[1] as Vector3
	if idx == 0:
		cam.rotation_degrees = Vector3.ZERO  # 朝 -Z（TACZ 第一人称前向）
	else:
		cam.look_at(_target, Vector3.UP)

func _save_shot(idx: int) -> void:
	var cam := root.get_node("Cam") as Camera3D
	var img := cam.get_viewport().get_texture().get_image()
	if img != null and img.get_width() > 0:
		var name: String = String(_views[idx][0])
		var suffix := OS.get_environment("SHOT_SUFFIX")
		var out := "user://tacz_%s%s.png" % [name, suffix]
		img.save_png(out)
		print("SAVED ", ProjectSettings.globalize_path(out))
	else:
		print("EMPTY IMAGE at shot ", idx)
