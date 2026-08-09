extends Node3D
## 通用区域/持续型技能（旧版 holyLight / blizzard / iceWall / meteor / stormDomain / flameArmor / drone 迁移）
## 释放：取相机前方 maxRange 内瞄准点（射线/固定距离）→ 按 skill_id 分派效果：
## - holyLight：圣光柱 + 立即范围魔法伤害
## - blizzard：暴风雪区域，每 tickMs 伤害（chill 减速简化省略）
## - iceWall：目标点生成冰墙列（StaticBody3D 阻挡）
## - meteor：延迟陨石坠落 → 火球爆炸三层 + 熔岩区持续灼烧
## - stormDomain：雷云跟随施法者，每 strikeIntervalMs 落雷（简化闪电线 + 传导伤害）
## - flameArmor：自身灼烧光环，每 tickMs 对周围敌人伤害
## - droneSkill：目标易伤标记（+damageBonusPercent 伤害，持续 duration）

const PX_TO_M := 0.014
signal cast_finished(hits, kills)

var _caster: Node3D
var _scene_root: Node
var _skill_id := ""
var _eff := {}
var _damage := 0
var _hits := 0
var _kills := 0
static var _dot_tex_cache: Texture2D

static func cast(scene_root: Node, caster: Node3D, level: int, matk: int, intt: int, skill_id: String, eff: Dictionary, on_finished: Callable = Callable()) -> void:
	var script := load("res://scripts/area_skill.gd")
	var node: Node3D = script.new()
	node.configure(caster, level, matk, intt, skill_id, eff, scene_root)
	scene_root.add_child(node)
	if on_finished.is_valid():
		node.cast_finished.connect(on_finished)
	node._run()

func configure(caster: Node3D, level: int, matk: int, intt: int, skill_id: String, eff: Dictionary, scene_root: Node) -> void:
	_caster = caster
	_scene_root = scene_root
	_skill_id = skill_id
	_eff = eff
	var base := float(eff.get("damageBase", 0.0))
	var mul := float(eff.get("magicMul", 0.0))
	var imul := float(eff.get("intMul", 0.0))
	_damage = maxi(1, floori(base + matk * mul + intt * imul))

func _run() -> void:
	match _skill_id:
		"holyLight":
			_holy_light()
			queue_free()
		"blizzard":
			_blizzard()
		"iceWall":
			_ice_wall()
			queue_free()
		"meteor":
			_meteor()
		"stormDomain":
			_storm_domain()
		"flameArmor":
			_flame_armor()
		"droneSkill":
			_drone()
			queue_free()

func _aim_point() -> Vector3:
	var cam := _find_cam()
	if cam == null:
		return _caster.global_position - _caster.global_transform.basis.z * 4.0
	var fwd := -cam.global_transform.basis.z
	var origin := cam.global_position
	var max_range := float(_eff.get("maxRange", 500.0)) * PX_TO_M
	var query := PhysicsRayQueryParameters3D.create(origin, origin + fwd * max_range, 3)
	var hit := get_world_3d().direct_space_state.intersect_ray(query)
	if hit:
		return hit.position
	return origin + fwd * minf(max_range, 6.0)

func _find_cam() -> Camera3D:
	if _caster == null:
		return null
	for c in _caster.get_children():
		if c is Camera3D:
			return c
	return null

## ---------- 圣光：光柱 + 立即范围伤害 ----------
func _holy_light() -> void:
	var pos := _aim_point()
	_light_column(pos, Color(1.0, 0.92, 0.55), 4.0)
	var radius := float(_eff.get("aimRadius", 200.0)) * PX_TO_M
	_aoe_hit(pos, radius, 1.0)
	cast_finished.emit(_hits, _kills)

## ---------- 暴风雪：区域持续 tick ----------
func _blizzard() -> void:
	var pos := _aim_point()
	position = pos
	_blizzard_visual()
	var tick_ms := float(_eff.get("tickMs", 500.0))
	var duration := float(_eff.get("duration", 5.0))
	var rx := float(_eff.get("radiusX", 200.0)) * PX_TO_M
	var rz := float(_eff.get("radiusY", 124.0)) * PX_TO_M
	_tick_area(tick_ms / 1000.0, duration, rx, rz, 1.0)

## ---------- 冰墙：目标点障碍列 ----------
func _ice_wall() -> void:
	var pos := _aim_point()
	var count := int(_eff.get("segmentCount", 5))
	var spacing := float(_eff.get("segmentSpacing", 28.0)) * PX_TO_M
	var seg_w := float(_eff.get("segmentWidth", 48.0)) * PX_TO_M
	var seg_h := float(_eff.get("segmentHeight", 64.0)) * PX_TO_M
	var duration := float(_eff.get("duration", 10.0))
	for i in count:
		var body := StaticBody3D.new()
		body.name = "IceWallSeg"
		body.collision_layer = 3
		body.position = pos + Vector3((float(i) - (count - 1) * 0.5) * spacing, seg_h * 0.5, 0)
		var col := CollisionShape3D.new()
		var box := BoxShape3D.new()
		box.size = Vector3(seg_w, seg_h, seg_w)
		col.shape = box
		body.add_child(col)
		var mi := MeshInstance3D.new()
		var bm := BoxMesh.new()
		bm.size = box.size
		var mat := StandardMaterial3D.new()
		mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
		mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
		mat.albedo_color = Color(0.62, 0.85, 1.0, 0.75)
		mat.emission_enabled = true
		mat.emission = Color(0.35, 0.6, 1.0)
		bm.material = mat
		mi.mesh = bm
		body.add_child(mi)
		_add_to_root(body)
		var t := get_tree().create_timer(duration)
		t.timeout.connect(func() -> void: body.queue_free())
	# 生成时碎裂音效可加；伤害结算（旧版生成时对碰撞敌人造成伤害）简化跳过

## ---------- 陨星：延迟坠落 + 爆炸 + 熔岩区 ----------
func _meteor() -> void:
	var pos := _aim_point()
	var fall := float(_eff.get("fallMs", 650.0)) / 1000.0
	var ball := _falling_ball(pos, fall)
	await get_tree().create_timer(fall).timeout
	if ball != null and is_instance_valid(ball):
		ball.queue_free()
	_explosion(pos, float(_eff.get("explosionRadius", 140.0)) * PX_TO_M)
	_lava_zone(pos, float(_eff.get("lavaRadius", 120.0)) * PX_TO_M,
		float(_eff.get("lavaDuration", 3.0)), float(_eff.get("lavaTickMs", 500.0)))
	queue_free()

func _falling_ball(pos: Vector3, fall: float) -> Node3D:
	var ball := Node3D.new()
	_add_to_root(ball)
	ball.position = pos + Vector3(0, 10, 0)
	var mi := MeshInstance3D.new()
	var sm := SphereMesh.new()
	sm.radius = 0.35
	sm.height = 0.7
	var mat := StandardMaterial3D.new()
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	mat.albedo_color = Color(1.0, 0.55, 0.18, 0.9)
	mat.emission_enabled = true
	mat.emission = Color(1.0, 0.45, 0.1)
	sm.material = mat
	mi.mesh = sm
	ball.add_child(mi)
	var tw := ball.create_tween()
	tw.tween_property(ball, "position", pos, fall).set_trans(Tween.TRANS_LINEAR)
	return ball

## ---------- 雷暴领域：跟随施法者定时落雷 ----------
func _storm_domain() -> void:
	var interval := float(_eff.get("strikeIntervalMs", 900.0)) / 1000.0
	var duration := float(_eff.get("duration", 10.0))
	var radius := float(_eff.get("radius", 220.0)) * PX_TO_M
	var strike_dmg := _damage
	var cloud := _make_cloud()
	var elapsed := 0.0
	while elapsed < duration:
		if _caster != null and is_instance_valid(_caster):
			cloud.global_position = _caster.global_position + Vector3(0, 2.6, 0)
		await get_tree().create_timer(interval).timeout
		elapsed += interval
		if _caster == null or not is_instance_valid(_caster):
			break
		var target := _nearest_hostile(_caster.global_position, radius)
		if target == null:
			continue
		var tpos: Vector3 = target.global_position + Vector3(0, 0.8, 0)
		_lightning_line(_caster.global_position + Vector3(0, 2.0, 0), tpos)
		var was_alive := int(target.get("hp")) > 0
		target.take_damage(strike_dmg)
		_hits += 1
		if was_alive and int(target.get("hp")) <= 0:
			_kills += 1
	cast_finished.emit(_hits, _kills)
	queue_free()

func _make_cloud() -> Node3D:
	var cloud := Node3D.new()
	cloud.name = "StormCloud"
	add_child(cloud)
	var mi := MeshInstance3D.new()
	var sm := SphereMesh.new()
	sm.radius = 0.7
	sm.height = 1.0
	var mat := StandardMaterial3D.new()
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	mat.albedo_color = Color(0.45, 0.4, 0.7, 0.55)
	mat.emission_enabled = true
	mat.emission = Color(0.35, 0.25, 0.7)
	sm.material = mat
	mi.mesh = sm
	cloud.add_child(mi)
	return cloud

## ---------- 灼锋焰甲：自身光环 tick ----------
func _flame_armor() -> void:
	var tick := float(_eff.get("auraTickMs", 500.0)) / 1000.0
	var duration := float(_eff.get("duration", 12.0))
	var radius := float(_eff.get("auraRadius", 130.0)) * PX_TO_M
	var light := OmniLight3D.new()
	light.light_color = Color(1.0, 0.45, 0.15)
	light.light_energy = 1.2
	light.omni_range = radius
	add_child(light)
	var elapsed := 0.0
	while elapsed < duration:
		await get_tree().create_timer(tick).timeout
		elapsed += tick
		if _caster == null or not is_instance_valid(_caster):
			break
		for c in _scene_root.get_children():
			if c == null or c == _caster or not c.has_method("take_damage") or String(c.name) == "Player":
				continue
			if (c.global_position - _caster.global_position).length() > radius:
				continue
			var dmg := maxi(1, floori(_damage * 0.35))
			var was_alive := int(c.get("hp")) > 0
			c.take_damage(dmg)
			_hits += 1
			if was_alive and int(c.get("hp")) <= 0:
				_kills += 1
	cast_finished.emit(_hits, _kills)
	queue_free()

## ---------- 无人机：目标易伤标记 ----------
func _drone() -> void:
	var pos := _aim_point()
	var radius := float(_eff.get("radius", 300.0)) * PX_TO_M
	var target := _nearest_hostile(pos, radius)
	if target == null:
		return
	var duration := float(_eff.get("duration", 15.0))
	var bonus := float(_eff.get("damageBonusPercent", 10.0)) / 100.0
	target.set("_vuln_mul", 1.0 + bonus)
	var drone := Sprite3D.new()
	drone.texture = _dot_tex()
	drone.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	drone.pixel_size = 0.0025
	drone.scale = Vector3.ONE * 0.8
	drone.position = target.global_position + Vector3(0, 1.8, 0)
	var dm := StandardMaterial3D.new()
	dm.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	dm.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	dm.blend_mode = BaseMaterial3D.BLEND_MODE_ADD
	dm.albedo_texture = _dot_tex()
	dm.albedo_color = Color(0.4, 0.9, 1.0, 0.8)
	drone.material_override = dm
	_add_to_root(drone)
	var t := get_tree().create_timer(duration)
	t.timeout.connect(func() -> void:
		if is_instance_valid(target):
			target.set("_vuln_mul", 1.0)
		drone.queue_free())

## ---------- 通用结算/特效 ----------
func _aoe_hit(pos: Vector3, radius: float, mul: float) -> void:
	for c in _scene_root.get_children():
		if c == null or c == _caster or not c.has_method("take_damage") or String(c.name) == "Player":
			continue
		var dist: float = (c.global_position - pos).length()
		if dist > radius:
			continue
		var ratio := 1.0 - clampf(dist / radius, 0.0, 1.0)
		var dmg := maxi(1, floori(_damage * mul * (0.5 + 0.5 * ratio)))
		var was_alive := int(c.get("hp")) > 0
		c.take_damage(dmg)
		_hits += 1
		if was_alive and int(c.get("hp")) <= 0:
			_kills += 1

func _tick_area(interval: float, duration: float, rx: float, rz: float, mul: float) -> void:
	var elapsed := 0.0
	while elapsed < duration:
		await get_tree().create_timer(interval).timeout
		elapsed += interval
		_aoe_hit(global_position, maxf(rx, rz) * 0.8, mul)
	cast_finished.emit(_hits, _kills)
	queue_free()

func _nearest_hostile(from: Vector3, range_m: float) -> Node3D:
	var best: Node3D = null
	var best_d := range_m
	for c in _scene_root.get_children():
		if c == null or c == _caster or not c.has_method("take_damage") or String(c.name) == "Player":
			continue
		var d: float = (c.global_position - from).length()
		if d <= best_d:
			best_d = d
			best = c
	return best

func _light_column(pos: Vector3, color: Color, height: float) -> void:
	var mi := MeshInstance3D.new()
	var cyl := CylinderMesh.new()
	cyl.top_radius = 0.5
	cyl.bottom_radius = 0.7
	cyl.height = height
	cyl.radial_segments = 12
	var mat := StandardMaterial3D.new()
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	mat.blend_mode = BaseMaterial3D.BLEND_MODE_ADD
	mat.albedo_color = color
	cyl.material = mat
	mi.mesh = cyl
	mi.position = pos + Vector3(0, height * 0.5, 0)
	_add_to_root(mi)
	var tw := mi.create_tween()
	tw.tween_method(func(v: float) -> void:
		mat.albedo_color.a = 0.55 * (1.0 - v)
		, 0.0, 1.0, float(_eff.get("fadeMs", 400.0)) / 1000.0)
	tw.tween_callback(func() -> void: mi.queue_free())

func _blizzard_visual() -> void:
	var p := GPUParticles3D.new()
	p.one_shot = false
	p.emitting = true
	p.amount = 90
	p.lifetime = 1.2
	p.local_coords = false
	p.position = global_position + Vector3(0, 2.5, 0)
	p.draw_pass_1 = _dot_pass(0.25, true)
	var pm := ParticleProcessMaterial.new()
	pm.direction = Vector3.DOWN
	pm.spread = 25.0
	pm.emission_shape = ParticleProcessMaterial.EMISSION_SHAPE_BOX
	pm.emission_box_extents = Vector3(1.6, 0.1, 1.0)
	pm.initial_velocity_min = 1.0
	pm.initial_velocity_max = 2.4
	pm.gravity = Vector3(0, -2.0, 0)
	pm.scale_min = 0.3
	pm.scale_max = 0.55
	pm.color_ramp = _ramp([
		Color(0.95, 0.99, 1.0, 0.85),
		Color(0.65, 0.85, 1.0, 0.0),
	], [0.0, 1.0])
	p.process_material = pm
	_add_to_root(p)
	_delayed_free(p, float(_eff.get("duration", 5.0)) + 1.5)

func _explosion(pos: Vector3, radius: float) -> void:
	var ring := MeshInstance3D.new()
	var torus := TorusMesh.new()
	torus.inner_radius = radius * 0.9
	torus.outer_radius = radius
	torus.rings = 18
	var mat := StandardMaterial3D.new()
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	mat.blend_mode = BaseMaterial3D.BLEND_MODE_ADD
	mat.albedo_color = Color(1.0, 0.5, 0.15, 0.9)
	torus.material = mat
	ring.mesh = torus
	ring.rotation_degrees = Vector3(90, 0, 0)
	ring.position = pos
	ring.scale = Vector3.ONE * 0.01
	_add_to_root(ring)
	var tw := ring.create_tween()
	tw.tween_method(func(t: float) -> void:
		ring.scale = Vector3.ONE * maxf(0.01, t)
		mat.albedo_color.a = (1.0 - t) * 0.9
		, 0.0, 1.0, 0.42).set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_OUT)
	tw.tween_callback(func() -> void: ring.queue_free())
	_aoe_hit(pos, radius, 1.0)
	cast_finished.emit(_hits, _kills)

func _lava_zone(pos: Vector3, radius: float, duration: float, tick_ms: float) -> void:
	var elapsed := 0.0
	var lava_dmg := maxi(1, floori(_damage * 0.25))
	while elapsed < duration:
		await get_tree().create_timer(tick_ms / 1000.0).timeout
		elapsed += tick_ms / 1000.0
		for c in _scene_root.get_children():
			if c == null or c == _caster or not c.has_method("take_damage") or String(c.name) == "Player":
				continue
			if (c.global_position - pos).length() > radius:
				continue
			c.take_damage(lava_dmg)

func _lightning_line(from: Vector3, to: Vector3) -> void:
	var node := Node3D.new()
	_add_to_root(node)
	node.position = from
	var dist := (to - from).length()
	var n := (to - from).cross(Vector3.UP)
	if n.length() < 0.001:
		n = Vector3.RIGHT
	n = n.normalized()
	var segs := 8
	var amp := maxf(0.15, dist * 0.09)
	var prev := Vector3.ZERO
	var dots: Array = []
	for i in range(1, segs + 1):
		var t := float(i) / float(segs)
		var p := (to - from) * t + n * (randf() * 2.0 - 1.0) * amp
		var mid := (prev + p) * 0.5 + n * (randf() * 2.0 - 1.0) * amp * 0.5
		dots.append(_bolt_dot(node, mid, 0.09, Color(0.5, 0.35, 1.0, 0.55)))
		dots.append(_bolt_dot(node, p, 0.06, Color(0.9, 0.88, 1.0, 0.9)))
		prev = p
	var tw := node.create_tween()
	tw.tween_interval(0.2)
	tw.tween_method(func(v: float) -> void:
		for d in dots:
			var m := (d as Sprite3D).material_override as StandardMaterial3D
			var c: Color = m.albedo_color
			c.a = c.a * v
			m.albedo_color = c
		, 1.0, 0.0, 0.18)
	tw.tween_callback(func() -> void: node.queue_free())

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

## ---------- 共用工具 ----------
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

func _dot_pass(size: float, additive: bool) -> QuadMesh:
	var q := QuadMesh.new()
	q.size = Vector2(size, size)
	var m := StandardMaterial3D.new()
	m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	m.albedo_texture = _dot_tex()
	m.albedo_color = Color.WHITE
	m.vertex_color_use_as_albedo = true
	if additive:
		m.blend_mode = BaseMaterial3D.BLEND_MODE_ADD
	q.material = m
	return q

func _ramp(colors: Array, offsets: Array) -> GradientTexture1D:
	var g := Gradient.new()
	g.colors = PackedColorArray(colors)
	g.offsets = PackedFloat32Array(offsets)
	var tex := GradientTexture1D.new()
	tex.gradient = g
	return tex

func _add_to_root(node: Node) -> void:
	var root: Node = _scene_root if _scene_root != null else get_tree().current_scene
	if root != null:
		root.add_child(node)
	else:
		get_parent().add_child(node)

func _delayed_free(node: Node, delay: float) -> void:
	var t := node.get_tree().create_timer(delay)
	t.timeout.connect(func() -> void: node.queue_free())
