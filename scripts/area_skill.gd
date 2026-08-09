extends Node3D
## 通用区域/持续型技能（旧版 holyLight / blizzard / iceWall / meteor / stormDomain / flameArmor / drone 迁移）
## 释放：取相机前方 maxRange 内瞄准点（射线/固定距离）→ 按 skill_id 分派效果：
## - holyLight：圣光柱 + 立即范围魔法伤害
## - blizzard：暴风雪区域，每 tickMs 伤害（chill 减速简化省略）
## - iceWall：目标点生成冰墙列（StaticBody3D 阻挡）
## - meteor：延迟陨石坠落 → 火球爆炸三层 + 熔岩区持续灼烧
## - stormDomain：雷云跟随施法者，每 strikeIntervalMs 落雷（首击立即），
##   主目标 + 传导链伤害，命中眩晕打断并叠加感电（叠满过载见 enemy.gd）
## - flameArmor：自身灼烧光环，每 tickMs 对周围敌人伤害
## - droneSkill：目标易伤标记（+damageBonusPercent 伤害，持续 duration）

const PX_TO_M := 0.014
signal cast_finished(hits, kills)

var _caster: Node3D
var _scene_root: Node
var _skill_id := ""
var _eff := {}
var _damage := 0
var _matk := 0
var _intt := 0
var _hits := 0
var _kills := 0
var _cloud: Node3D
var _cloud_arc_t := 0.0
var _cloud_mist_t := 0.0
var _cloud_spark_t := 0.0
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
	_matk = matk
	_intt = intt
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
			await _ice_wall()
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

## 雷云持续期驱动：云内电弧闪烁 + 蓝色云雾弥漫 + 云底电花坠落（旧版 StormCloudFx）
func _process(delta: float) -> void:
	if _cloud == null:
		return
	_cloud_arc_t -= delta
	if _cloud_arc_t <= 0.0:
		_cloud_arc_t = 0.26 + randf() * 0.26
		_cloud_arc()
	_cloud_mist_t -= delta
	if _cloud_mist_t <= 0.0:
		_cloud_mist_t = 0.22
		_cloud_mist()
	_cloud_spark_t -= delta
	if _cloud_spark_t <= 0.0:
		_cloud_spark_t = 0.15
		_cloud_spark()

func _cloud_arc() -> void:
	var node := Node3D.new()
	_cloud.add_child(node)
	var x0 := randf_range(-0.6, 0.6)
	var pts: Array = [Vector3(x0, 0.0, 0.0)]
	var cx := x0
	var cy := 0.0
	var segs := 4 + randi() % 3
	for i in segs:
		cx += randf_range(-0.18, 0.18)
		cy += randf_range(0.1, 0.24)
		pts.append(Vector3(cx, cy, 0))
	var dots: Array = []
	for i in range(pts.size() - 1):
		var a: Vector3 = pts[i]
		var b: Vector3 = pts[i + 1]
		for j in range(1, 4):
			var t := float(j) / 4.0
			var p := a.lerp(b, t) + Vector3(randf_range(-0.03, 0.03), 0, randf_range(-0.03, 0.03))
			dots.append(_bolt_dot(node, p, 0.05, Color(0x6a / 255.0, 0x9f / 255.0, 1.0, 0.9)))
			dots.append(_bolt_dot(node, p, 0.028, Color.WHITE))
	var tw := node.create_tween()
	tw.tween_method(func(v: float) -> void:
		for d in dots:
			var m := (d as Sprite3D).material_override as StandardMaterial3D
			var c2: Color = m.albedo_color
			c2.a = c2.a * v
			m.albedo_color = c2
		, 1.0, 0.0, 0.16)
	tw.tween_callback(func() -> void: node.queue_free())

func _cloud_mist() -> void:
	var a := randf() * TAU
	var rr := randf_range(0.7, 1.8)
	var pos := Vector3(cos(a) * rr * 0.5, sin(a) * rr * 0.22 + randf_range(-0.2, 0.2), cos(a) * rr * 0.3)
	var sp := _bolt_dot(_cloud, pos, 0.3, Color(0x3f / 255.0, 0x66 / 255.0, 0xb8 / 255.0, 0.22))
	var tw := sp.create_tween()
	tw.tween_property(sp, "scale", sp.scale * 1.5, 1.6)
	tw.parallel().tween_method(func(v: float) -> void:
		var m := sp.material_override as StandardMaterial3D
		var c2: Color = m.albedo_color
		c2.a = c2.a * v
		m.albedo_color = c2
		, 1.0, 0.0, 1.6)
	tw.tween_callback(func() -> void: sp.queue_free())

func _cloud_spark() -> void:
	var sx := randf_range(-0.9, 0.9)
	var sp := _bolt_dot(_cloud, Vector3(sx, 0.0, 0.0), 0.035, Color(0.9, 0.94, 1.0, 0.95))
	var tw := sp.create_tween()
	tw.tween_property(sp, "position", Vector3(sx + randf_range(-0.15, 0.15), randf_range(-1.6, -1.0), randf_range(-0.1, 0.1)), 0.7)
	tw.parallel().tween_method(func(v: float) -> void:
		var m := sp.material_override as StandardMaterial3D
		var c2: Color = m.albedo_color
		c2.a = c2.a * v
		m.albedo_color = c2
		, 1.0, 0.0, 0.7)
	tw.tween_callback(func() -> void: sp.queue_free())

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
	var buff := {
		"type": "chill",
		"stacks": int(_eff.get("chillStacks", 1)),
		"duration_ms": int(_eff.get("chillDurationMs", 2500)),
		"slow_percent": float(_eff.get("chillSlowPercent", 0.035)),
	}
	_tick_area(tick_ms / 1000.0, duration, rx, rz, 1.0, buff)

## ---------- 冰墙：目标点障碍列 ----------
func _ice_wall() -> void:
	var pos := _aim_point()
	var count := int(_eff.get("segmentCount", 5))
	var spacing := float(_eff.get("segmentSpacing", 28.0)) * PX_TO_M
	var seg_w := float(_eff.get("segmentWidth", 48.0)) * PX_TO_M
	var seg_h := float(_eff.get("segmentHeight", 64.0)) * PX_TO_M
	var duration := float(_eff.get("duration", 10.0))
	var seg_positions: Array = []
	for i in count:
		var body := StaticBody3D.new()
		body.name = "IceWallSeg"
		body.collision_layer = 3
		body.position = pos + Vector3((float(i) - (count - 1) * 0.5) * spacing, seg_h * 0.5, 0)
		seg_positions.append(body.position)
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
	# 冰墙寒冷光环（旧版 chillRadius / chillIntervalMs）：范围内敌人持续叠寒冷
	var chill_r := float(_eff.get("chillRadius", 100.0)) * PX_TO_M
	var chill_interval := float(_eff.get("chillIntervalMs", 1000.0)) / 1000.0
	var buff := {
		"type": "chill",
		"stacks": int(_eff.get("chillStacks", 1)),
		"duration_ms": int(_eff.get("chillDurationMs", 2500)),
		"slow_percent": float(_eff.get("chillSlowPercent", 0.035)),
	}
	var elapsed := 0.0
	while elapsed < duration:
		await get_tree().create_timer(chill_interval).timeout
		elapsed += chill_interval
		for c in _scene_root.get_children():
			if c == null or c == _caster or not c.has_method("take_damage") or String(c.name) == "Player":
				continue
			for sp in seg_positions:
				if (c.global_position - sp).length() <= chill_r:
					_apply_buff(c, buff)
					break

## ---------- 陨星：延迟坠落 + 爆炸 + 熔岩区 ----------
func _meteor() -> void:
	var pos := _aim_point()
	var fall := float(_eff.get("fallMs", 650.0)) / 1000.0
	var ball := _falling_ball(pos, fall)
	await get_tree().create_timer(fall).timeout
	if ball != null and is_instance_valid(ball):
		ball.queue_free()
	var explosion_radius := float(_eff.get("explosionRadius", 140.0)) * PX_TO_M
	_explosion(pos, explosion_radius)
	_apply_explosion_debuffs(pos, explosion_radius)
	var lava_burn := {
		"type": "burn",
		"stacks": int(_eff.get("lavaBurnStacks", 1)),
		"duration_ms": int(_eff.get("lavaBurnDurationMs", 2500)),
		"damage_mul": float(_eff.get("lavaBurnDamageMul", 0.3)),
	}
	await _lava_zone(pos, float(_eff.get("lavaRadius", 120.0)) * PX_TO_M,
		float(_eff.get("lavaDuration", 3.0)), float(_eff.get("lavaTickMs", 500.0)), lava_burn)
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
	var chain_extra := maxi(0, int(_eff.get("chainExtraTargets", 1)))
	var chain_range := float(_eff.get("chainRange", 160.0)) * PX_TO_M
	var chain_decay := float(_eff.get("chainDecay", 0.3))
	var stun_ms := int(_eff.get("stunMs", 0))
	var elect_stacks := maxi(0, int(_eff.get("electrifyStacks", 0)))
	var elect_ms := int(_eff.get("electrifyDurationMs", 0))
	# 旧版落雷伤害用 strikeDamageBase/strikeMagicMul/strikeIntMul（非通用 damageBase）
	var strike_dmg := maxi(1, floori(float(_eff.get("strikeDamageBase", 25.0))
		+ _matk * float(_eff.get("strikeMagicMul", 0.5)) + _intt * float(_eff.get("strikeIntMul", 0.5))))
	var cloud := _make_cloud()
	var elapsed := 0.0
	while elapsed < duration:
		if _caster != null and is_instance_valid(_caster):
			cloud.global_position = _caster.global_position + Vector3(0, 2.6, 0)
		# 旧版首击立即（timer 从 0 起跳），此后每 interval 一击
		if elapsed > 0.0:
			await get_tree().create_timer(interval).timeout
		elapsed += interval
		if _caster != null and is_instance_valid(_caster):
			cloud.global_position = _caster.global_position + Vector3(0, 2.6, 0)
			var main := _nearest_hostile(_caster.global_position, radius)
			if main != null:
				# 传导链（旧版 chainExtraTargets）：主目标 → 邻近传导，每跳衰减
				var chain: Array = [main]
				var cursor: Node3D = main
				for hop in range(chain_extra):
					var next := _nearest_hostile(cursor.global_position, chain_range, chain)
					if next == null:
						break
					chain.append(next)
					cursor = next
				for i in chain.size():
					var decay_mul := pow(1.0 - chain_decay, i)
					var dmg := maxi(1, floori(strike_dmg * decay_mul))
					var target := chain[i] as Node3D
					var src_pos: Vector3 = cloud.global_position \
						if i == 0 else (chain[i - 1] as Node3D).global_position + Vector3(0, 0.8, 0)
					var tpos: Vector3 = target.global_position + Vector3(0, 0.8, 0)
					_lightning_line(src_pos, tpos)
					_spawn_hit_fx(target.global_position, decay_mul)
					var was_alive := _hp_of(target) > 0
					if target.has_method("take_damage"):
						target.take_damage(dmg, "electric", _caster)
					if elect_stacks > 0 and target.has_method("apply_electrified"):
						target.apply_electrified(elect_stacks, elect_ms, _matk, _intt)
					if stun_ms > 0 and target.has_method("apply_stun"):
						target.apply_stun(stun_ms)
					_hits += 1
					if was_alive and _hp_of(target) <= 0:
						_kills += 1
	cast_finished.emit(_hits, _kills)
	queue_free()

func _make_cloud() -> Node3D:
	var cloud := Node3D.new()
	cloud.name = "StormCloud"
	add_child(cloud)
	# 旧版 StormCloudFx：四层蓝调柔边云（深蓝黑→靛蓝→电光蓝→高光），按 radius/220 等比缩放
	var scale := maxf(0.8, float(_eff.get("radius", 220.0)) / 220.0)
	var layers: Array = [
		{ "tint": Color(0x14 / 255.0, 0x1b / 255.0, 0x2e / 255.0), "count": 18, "spread": 1.0, "size_min": 0.62, "size_max": 1.0, "alpha": 0.92, "y_off": 0.0 },
		{ "tint": Color(0x23 / 255.0, 0x3a / 255.0, 0x66 / 255.0), "count": 14, "spread": 0.84, "size_min": 0.5, "size_max": 0.82, "alpha": 0.88, "y_off": -0.16 },
		{ "tint": Color(0x3f / 255.0, 0x66 / 255.0, 0xb8 / 255.0), "count": 10, "spread": 0.62, "size_min": 0.4, "size_max": 0.64, "alpha": 0.82, "y_off": -0.30 },
		{ "tint": Color(0x8f / 255.0, 0xb8 / 255.0, 0xff / 255.0), "count": 6, "spread": 0.42, "size_min": 0.28, "size_max": 0.46, "alpha": 0.72, "y_off": -0.42 },
	]
	for L in layers:
		var tint: Color = L["tint"]
		for i in range(int(L["count"])):
			var rr := sqrt(randf()) * float(L["spread"])
			var a := randf() * TAU
			var ox := cos(a) * rr * 1.34 * scale
			var oy := sin(a) * rr * 0.62 * scale + float(L["y_off"]) * 0.81 * scale
			var size := 1.29 * scale * (float(L["size_min"]) + randf() * (float(L["size_max"]) - float(L["size_min"])))
			var sp := _bolt_dot(cloud, Vector3(ox, oy, 0), size * 0.5, Color(tint.r, tint.g, tint.b, float(L["alpha"]) * (0.75 + randf() * 0.25)))
			sp.scale = Vector3.ONE * (size / 0.16)
	_cloud = cloud
	return cloud

## ---------- 灼锋焰甲：自身光环 tick ----------
func _flame_armor() -> void:
	var tick := float(_eff.get("auraTickMs", 500.0)) / 1000.0
	var duration := float(_eff.get("duration", 12.0))
	var radius := float(_eff.get("auraRadius", 130.0)) * PX_TO_M
	if _caster != null and _caster.has_method("apply_buff"):
		_caster.apply_buff("flameArmor", int(duration * 1000.0))
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
			var was_alive := _hp_of(c) > 0
			c.take_damage(dmg)
			_hits += 1
			if was_alive and _hp_of(c) <= 0:
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
	# 旧版 droneSkill：目标无人机易伤（每层所有伤害 +10%），持续 duration
	if target.has_method("apply_drone_vulnerability"):
		target.apply_drone_vulnerability(1, int(duration * 1000.0))
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
		if is_instance_valid(target) and target.has_method("remove_buff"):
			target.remove_buff("droneVulnerability")
		drone.queue_free())

## ---------- 通用结算/特效 ----------
func _aoe_hit(pos: Vector3, radius: float, mul: float, buff: Dictionary = {}) -> void:
	for c in _scene_root.get_children():
		if c == null or c == _caster or not c.has_method("take_damage") or String(c.name) == "Player":
			continue
		var dist: float = (c.global_position - pos).length()
		if dist > radius:
			continue
		var ratio := 1.0 - clampf(dist / radius, 0.0, 1.0)
		var dmg := maxi(1, floori(_damage * mul * (0.5 + 0.5 * ratio)))
		var was_alive := _hp_of(c) > 0
		c.take_damage(dmg)
		_hits += 1
		if was_alive and _hp_of(c) <= 0:
			_kills += 1
		_apply_buff(c, buff)

func _tick_area(interval: float, duration: float, rx: float, rz: float, mul: float, buff: Dictionary = {}) -> void:
	var elapsed := 0.0
	while elapsed < duration:
		await get_tree().create_timer(interval).timeout
		elapsed += interval
		_aoe_hit(global_position, maxf(rx, rz) * 0.8, mul, buff)
	cast_finished.emit(_hits, _kills)
	queue_free()

## 通用 buff 应用分发（旧版技能 buff 字段 → enemy apply_* 接口）
func _apply_buff(target: Node3D, buff: Dictionary) -> void:
	if buff.is_empty() or target == null:
		return
	var type: String = buff.get("type", "")
	var stacks_n := int(buff.get("stacks", 1))
	var duration_ms := int(buff.get("duration_ms", 0))
	match type:
		"chill":
			if target.has_method("apply_chill"):
				target.apply_chill(stacks_n, duration_ms, float(buff.get("slow_percent", 0.05)))
		"burn":
			if target.has_method("apply_burn"):
				target.apply_burn(_caster, stacks_n, duration_ms, float(buff.get("damage_mul", 0.5)), _matk)
		"stun":
			if target.has_method("apply_stun"):
				target.apply_stun(duration_ms)
		"droneVulnerability":
			if target.has_method("apply_drone_vulnerability"):
				target.apply_drone_vulnerability(stacks_n, duration_ms)

## 陨星爆炸：主爆炸眩晕 + 灼烧（旧版 stunMs / burnStacks / burnDurationMs / burnDamageMul）
func _apply_explosion_debuffs(pos: Vector3, radius: float) -> void:
	var burn := {
		"type": "burn",
		"stacks": int(_eff.get("burnStacks", 3)),
		"duration_ms": int(_eff.get("burnDurationMs", 3500)),
		"damage_mul": float(_eff.get("burnDamageMul", 0.5)),
	}
	var stun_ms := int(_eff.get("stunMs", 0))
	for c in _scene_root.get_children():
		if c == null or c == _caster or not c.has_method("take_damage") or String(c.name) == "Player":
			continue
		if (c.global_position - pos).length() > radius:
			continue
		if stun_ms > 0 and c.has_method("apply_stun"):
			c.apply_stun(stun_ms)
		_apply_buff(c, burn)

func _nearest_hostile(from: Vector3, range_m: float, exclude: Array = []) -> Node3D:
	var best: Node3D = null
	var best_d := range_m
	for c in _scene_root.get_children():
		if c == null or c == _caster or not c.has_method("take_damage") or String(c.name) == "Player":
			continue
		if exclude.has(c):
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

func _lava_zone(pos: Vector3, radius: float, duration: float, tick_ms: float, burn: Dictionary = {}) -> void:
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
			_apply_buff(c, burn)

## 旧版 LightningBoltEffect 移植：中点位移锯齿 → 按比例重采样色块链，
## 每点四层圆块（外层辉光 ADD + 内芯），施法端粗 → 目标端细；形态创建时定格
func _lightning_line(from: Vector3, to: Vector3, opts: Dictionary = {}) -> void:
	var node := Node3D.new()
	_add_to_root(node)
	node.position = from
	var local_to := to - from
	var dist := local_to.length()
	if dist < 0.001:
		node.queue_free()
		return
	var n := local_to.cross(Vector3.UP)
	if n.length() < 0.001:
		n = Vector3.RIGHT
	n = n.normalized()
	var segs := maxi(4, int(opts.get("segments", 9)))
	var jitter := float(opts.get("jitter", 0.10))
	var uniform := bool(opts.get("uniform", false))
	var width_scale := float(opts.get("widthScale", 1.0))
	var amp := maxf(0.14, dist * jitter)
	var pts: Array = [Vector3.ZERO]
	for i in range(1, segs):
		var t := float(i) / float(segs)
		var off := (randf() * 2.0 - 1.0) * amp
		pts.append(local_to * t + n * off)
	pts.append(local_to)
	# 细分 + Chaikin 平滑（保留端点）
	var dense: Array = []
	for i in range(pts.size() - 1):
		dense.append(pts[i])
		dense.append((pts[i] + pts[i + 1]) * 0.5)
	dense.append(pts[pts.size() - 1])
	var smooth: Array = []
	for i in range(dense.size() - 1):
		var p1: Vector3 = dense[i]
		var p2: Vector3 = dense[i + 1]
		if i == 0:
			smooth.append(p1)
		smooth.append(p1 * 0.75 + p2 * 0.25)
		smooth.append(p1 * 0.25 + p2 * 0.75)
		if i == dense.size() - 2:
			smooth.append(p2)
	# 按步长重采样成连续色块链，每点烘焙大小随机因子
	var step_m := 0.06
	var chain: Array = []
	var acc := 0.0
	for i in range(smooth.size() - 1):
		var p1: Vector3 = smooth[i]
		var p2: Vector3 = smooth[i + 1]
		var seg_len := p1.distance_to(p2)
		if seg_len < 0.001:
			continue
		var t := acc / seg_len
		while t <= 1.0:
			chain.append({ "pos": p1.lerp(p2, t), "s": 1.0 if uniform else 0.75 + randf() * 0.5 })
			acc += step_m
			t = acc / seg_len
		acc -= seg_len
	chain.append({ "pos": smooth[smooth.size() - 1], "s": 1.0 })
	# 四层圆块：外层辉光 ADD + 内芯色块；源端粗 → 目标端细
	var dots: Array = []
	var layers_cfg: Array = [
		{ "color": Color(0x6a / 255.0, 0x4b / 255.0, 1.0), "r0": 0.42, "r1": 0.07, "alpha": 0.26, "add": true },
		{ "color": Color(0xa9 / 255.0, 0x8f / 255.0, 1.0), "r0": 0.27, "r1": 0.06, "alpha": 0.18, "add": true },
		{ "color": Color(0xdc / 255.0, 0xd6 / 255.0, 1.0), "r0": 0.15, "r1": 0.03, "alpha": 0.88, "add": false },
		{ "color": Color.WHITE, "r0": 0.07, "r1": 0.014, "alpha": 0.92, "add": false },
	]
	var n_chain := chain.size()
	for i in n_chain:
		var c: Dictionary = chain[i]
		var t := float(i) / float(maxi(1, n_chain - 1))
		for L in layers_cfg:
			var r := lerpf(float(L["r0"]), float(L["r1"]), t) * float(c["s"]) * width_scale
			if r < 0.005:
				continue
			dots.append(_bolt_dot(node, c["pos"], r, Color(float(L["color"].r), float(L["color"].g), float(L["color"].b), float(L["alpha"]))))
			if not bool(L["add"]):
				var m := (dots[dots.size() - 1] as Sprite3D).material_override as StandardMaterial3D
				m.blend_mode = BaseMaterial3D.BLEND_MODE_MIX
	var life := float(opts.get("durationMs", 420.0)) / 1000.0
	var fade := float(opts.get("fadeMs", 220.0)) / 1000.0
	var tw := node.create_tween()
	tw.tween_interval(life)
	tw.tween_method(func(v: float) -> void:
		for d in dots:
			var m := (d as Sprite3D).material_override as StandardMaterial3D
			var c2: Color = m.albedo_color
			c2.a = c2.a * v
			m.albedo_color = c2
		, 1.0, 0.0, fade)
	tw.tween_callback(func() -> void: node.queue_free())

## 落雷命中特效（旧版 _spawnHitFx）：紫色冲击波 + 白/紫叠加粒子，随传导衰减缩放
func _spawn_hit_fx(pos: Vector3, decay_mul: float) -> void:
	var scale := 0.75 + 0.25 * decay_mul
	var ground := pos + Vector3(0, -0.8, 0)
	var ring := MeshInstance3D.new()
	var torus := TorusMesh.new()
	var r := 1.06 * scale
	torus.inner_radius = r * 0.72
	torus.outer_radius = r
	torus.rings = 16
	var mat := StandardMaterial3D.new()
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	mat.blend_mode = BaseMaterial3D.BLEND_MODE_ADD
	mat.albedo_color = Color(0xa9 / 255.0, 0x8f / 255.0, 1.0, 0.55)
	torus.material = mat
	ring.mesh = torus
	ring.rotation_degrees = Vector3(90, 0, 0)
	ring.position = ground
	ring.scale = Vector3.ONE * 0.01
	_add_to_root(ring)
	var tw := ring.create_tween()
	tw.tween_method(func(t: float) -> void:
		ring.scale = Vector3.ONE * maxf(0.01, t)
		mat.albedo_color.a = (1.0 - t) * 0.55
		, 0.0, 1.0, 0.38).set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_OUT)
	tw.tween_callback(func() -> void: ring.queue_free())
	# 白/紫叠加粒子迸溅（旧版 burstParticles impact_dot ADD）
	var node := Node3D.new()
	node.position = ground
	_add_to_root(node)
	var tint_pool: Array = [Color.WHITE, Color(0xf0 / 255.0, 0xe9 / 255.0, 1.0), Color(0xdd / 255.0, 0xd2 / 255.0, 1.0), Color(0x8f / 255.0, 0x7b / 255.0, 1.0)]
	var count := int(round(16.0 * scale))
	var dots: Array = []
	for i in count:
		var sp := _bolt_dot(node, Vector3.ZERO, 0.045, Color(tint_pool[i % tint_pool.size()].r, tint_pool[i % tint_pool.size()].g, tint_pool[i % tint_pool.size()].b, 1.0))
		dots.append(sp)
		var ang := randf() * TAU
		var vel := randf_range(0.6, 2.8)
		var dir := Vector3(cos(ang) * vel, randf_range(0.3, 1.4), sin(ang) * vel)
		var tw2 := sp.create_tween()
		tw2.tween_property(sp, "position", dir, randf_range(0.32, 0.6)).set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_OUT)
		tw2.parallel().tween_method(func(v: float) -> void:
			var m := sp.material_override as StandardMaterial3D
			var c2: Color = m.albedo_color
			c2.a = c2.a * v
			m.albedo_color = c2
			, 1.0, 0.0, randf_range(0.32, 0.6))
		tw2.tween_callback(func() -> void: sp.queue_free())
	await get_tree().create_timer(0.7).timeout
	node.queue_free()

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

func _hp_of(node: Object) -> int:
	var h = node.get("_hp")
	return int(h) if h != null else 0
