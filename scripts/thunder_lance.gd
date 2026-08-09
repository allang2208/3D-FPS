extends Node3D
## 贯穿雷枪（旧版 ThunderLanceSystem 简化迁移：蓄力机制暂缓，按满蓄力立即释放）
## 沿相机瞄准方向发射电磁贯穿光束：命中路径上所有敌人全额伤害（感电层数加成简化省略），
## 射程尽头/撞墙处电爆（蓝紫冲击波 + 白紫粒子）。

const PX_TO_M := 0.014
signal cast_finished(hits, kills)

var _caster: Node3D
var _scene_root: Node
var _damage := 0
var _max_range := 12.0
var _hits := 0
var _kills := 0
static var _dot_tex_cache: Texture2D

static func cast(scene_root: Node, caster: Node3D, level: int, matk: int, intt: int, eff: Dictionary, on_finished: Callable = Callable()) -> void:
	var script := load("res://scripts/thunder_lance.gd")
	var node: Node3D = script.new()
	node.configure(caster, level, matk, intt, eff, scene_root)
	scene_root.add_child(node)
	if on_finished.is_valid():
		node.cast_finished.connect(on_finished)
	node._fire()

func configure(caster: Node3D, level: int, matk: int, intt: int, eff: Dictionary, scene_root: Node) -> void:
	_caster = caster
	_scene_root = scene_root
	_max_range = float(eff.get("maxRange", 900.0)) * PX_TO_M
	_damage = maxi(1, floori(float(eff.get("lanceDamageBase", 110.0))
		+ matk * float(eff.get("lanceMagicMul", 1.8)) + intt * float(eff.get("lanceIntMul", 2.0))))

func _fire() -> void:
	if _caster == null or not is_instance_valid(_caster):
		queue_free()
		return
	var cam: Camera3D = null
	for c in _caster.get_children():
		if c is Camera3D:
			cam = c
			break
	var origin := _caster.global_position
	var fwd := -_caster.global_transform.basis.z
	if cam != null:
		origin = cam.global_position
		fwd = -cam.global_transform.basis.z
	var end := origin + fwd * _max_range
	# 撞墙截断
	var query := PhysicsRayQueryParameters3D.create(origin, end, 3)
	var hit := get_world_3d().direct_space_state.intersect_ray(query)
	if hit:
		end = hit.position
	# 光束特效
	_beam(origin, end)
	# 贯穿路径上所有敌人（简化：按射线垂直距离判定）
	for c in _scene_root.get_children():
		if c == null or c == _caster or not c.has_method("take_damage") or String(c.name) == "Player":
			continue
		var p: Vector3 = c.global_position
		if _dist_to_segment(p, origin, end) > 0.8:
			continue
		if p.distance_to(origin) > _max_range + 1.0:
			continue
		var was_alive := _hp_of(c) > 0
		c.take_damage(_damage)
		_hits += 1
		if was_alive and _hp_of(c) <= 0:
			_kills += 1
	# 末端电爆
	_electric_boom(end)
	cast_finished.emit(_hits, _kills)
	queue_free()

func _dist_to_segment(p: Vector3, a: Vector3, b: Vector3) -> float:
	var ab := b - a
	var len2 := ab.length_squared()
	if len2 < 1e-6:
		return p.distance_to(a)
	var t := clampf((p - a).dot(ab) / len2, 0.0, 1.0)
	return p.distance_to(a + ab * t)

func _beam(from: Vector3, to: Vector3) -> void:
	var node := Node3D.new()
	_add_to_root(node)
	node.position = from
	var dir := (to - from).normalized()
	var len := (to - from).length()
	var n := dir.cross(Vector3.UP)
	if n.length() < 0.001:
		n = Vector3.RIGHT
	n = n.normalized()
	var dots: Array = []
	var steps := maxi(8, int(len / 0.35))
	var prev := Vector3.ZERO
	for i in range(1, steps + 1):
		var t := float(i) / float(steps)
		var p := dir * len * t + n * (randf() * 2.0 - 1.0) * 0.12
		var mid := (prev + p) * 0.5 + n * (randf() * 2.0 - 1.0) * 0.18
		dots.append(_bolt_dot(node, mid, 0.12, Color(0.5, 0.35, 1.0, 0.5)))
		dots.append(_bolt_dot(node, p, 0.08, Color(0.95, 0.92, 1.0, 0.95)))
		prev = p
	var tw := node.create_tween()
	tw.tween_interval(0.35)
	tw.tween_method(func(v: float) -> void:
		for d in dots:
			var m := (d as Sprite3D).material_override as StandardMaterial3D
			var c: Color = m.albedo_color
			c.a = c.a * v
			m.albedo_color = c
		, 1.0, 0.0, 0.2)
	tw.tween_callback(func() -> void: node.queue_free())

func _electric_boom(pos: Vector3) -> void:
	var ring := MeshInstance3D.new()
	var torus := TorusMesh.new()
	var r := 0.75
	torus.inner_radius = r * 0.9
	torus.outer_radius = r
	torus.rings = 18
	var mat := StandardMaterial3D.new()
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	mat.blend_mode = BaseMaterial3D.BLEND_MODE_ADD
	mat.albedo_color = Color(0.66, 0.42, 1.0, 0.9)
	torus.material = mat
	ring.mesh = torus
	ring.rotation_degrees = Vector3(90, 0, 0)
	ring.position = pos
	ring.scale = Vector3.ONE * 0.01
	_add_to_root(ring)
	var tw := ring.create_tween()
	tw.tween_method(func(t: float) -> void:
		ring.scale = Vector3.ONE * maxf(0.01, t)
		var flick: float = 0.6 + 0.4 * sin(t * TAU * 5.0)
		mat.albedo_color.a = (1.0 - t) * 0.9 * flick
		, 0.0, 1.0, 0.38).set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_OUT)
	tw.tween_callback(func() -> void: ring.queue_free())

func _bolt_dot(parent: Node3D, local_pos: Vector3, radius: float, color: Color) -> Sprite3D:
	var sp := Sprite3D.new()
	sp.texture = _dot_tex()
	sp.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	sp.pixel_size = 0.0025
	sp.position = local_pos
	sp.scale = Vector3.ONE * maxf(0.01, radius / 0.16)
	var m := StandardMaterial3D.new()
	m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	m.blend_mode = BaseMaterial3D.BLEND_MODE_ADD
	m.albedo_texture = _dot_tex()
	m.albedo_color = color
	sp.material_override = m
	parent.add_child(sp)
	return sp

func _dot_tex() -> Texture2D:
	if _dot_tex_cache != null:
		return _dot_tex_cache
	var size := 64
	var img := Image.create(size, size, false, Image.FORMAT_RGBA8)
	for y in size:
		for x in size:
			var dx := (x + 0.5) / size * 2.0 - 1.0
			var dy := (y + 0.5) / size * 2.0 - 1.0
			var d := sqrt(dx * dx + dy * dy)
			var a := clampf(1.0 - d, 0.0, 1.0)
			a = a * a
			img.set_pixel(x, y, Color(1, 1, 1, a))
	_dot_tex_cache = ImageTexture.create_from_image(img)
	return _dot_tex_cache

func _add_to_root(node: Node) -> void:
	var root: Node = _scene_root if _scene_root != null else get_tree().current_scene
	if root != null:
		root.add_child(node)
	else:
		get_parent().add_child(node)

func _hp_of(node: Object) -> int:
	var h = node.get("_hp")
	return int(h) if h != null else 0
