extends Node3D
## 闪电技能（单段锁定+传导迁移，旧版 LightningStrikeSystem / skills.json lightningStrike）
## 释放 = 锁定相机准星前方 aimRadius 内最近敌方（且距施法者 ≤ maxRange）：
## 蓝紫闪电链连接（施法端粗→目标端细，锯齿折线 + 软点链），主目标全额伤害；
## 随后在 chainRange 内最近敌对单位传导，每跳伤害 ×(1−chainDecay)，最多 chainTargets 跳。
## 每个命中点附带蓝紫冲击波 + 白紫粒子爆炸。无目标/超距/被遮挡 → 释放失败（不耗魔不冷却）。

const PX_TO_M := 0.014
const CAST_SOUNDS := [
	"res://assets/sfx/lightning-1.mp3",
	"res://assets/sfx/lightning-2.mp3",
]

var _caster: Node3D
var _damage := 30
var _effect := {}
var _scene_root: Node
signal cast_finished(hits, kills)
static var _dot_tex_cache: Texture2D

## 释放闪电；成功返回 {ok:true, hits, kills}，失败返回 {ok:false}
static func cast(scene_root: Node, caster: Node3D, level: int, matk: int, intt: int, effect: Dictionary) -> Dictionary:
	var script := load("res://scripts/lightning.gd")
	var ln: Node3D = script.new()
	ln.configure(caster, level, matk, intt, effect, scene_root)
	scene_root.add_child(ln)
	return ln._cast()

func configure(caster: Node3D, level: int, matk: int, intt: int, effect: Dictionary, scene_root: Node) -> void:
	_caster = caster
	_effect = effect
	_scene_root = scene_root
	_damage = floori(effect.get("damage_base", 20.0) + matk * float(effect.get("magic_mul", 1.0))
		+ intt * float(effect.get("int_mul", 1.0)))

func _cast() -> Dictionary:
	if _caster == null or not is_instance_valid(_caster):
		queue_free()
		return {"ok": false}
	var primary := _acquire_target()
	if primary == null:
		queue_free()
		return {"ok": false}
	_play_cast_sound()
	# 传导链：主目标 → chainRange 内最近（排除已命中）
	var chain: Array = [primary]
	var cursor: Node3D = primary
	var chain_targets := maxi(1, int(_effect.get("chain_targets", 1)))
	for hop in range(1, chain_targets):
		var next := _nearest_hostile(cursor.global_position, float(_effect.get("chain_range_m", 2.8)), chain)
		if next == null:
			break
		chain.append(next)
		cursor = next
	# 逐目标结算
	var hits := 0
	var kills := 0
	for i in chain.size():
		var decay_mul := pow(1.0 - float(_effect.get("chain_decay", 0.1)), i)
		var dmg := maxi(1, floori(_damage * decay_mul))
		var src_pos: Vector3 = _caster.global_position if i == 0 else (chain[i - 1] as Node3D).global_position
		var tgt_pos: Vector3 = (chain[i] as Node3D).global_position + Vector3(0, 0.9, 0)
		_lightning_bolt(src_pos, tgt_pos)
		_impact_bolt(tgt_pos, decay_mul)
		var target := chain[i] as Node3D
		var was_alive := int(target.get("hp")) > 0
		target.take_damage(dmg)
		hits += 1
		if was_alive and int(target.get("hp")) <= 0:
			kills += 1
	cast_finished.emit(hits, kills)
	queue_free()
	return {"ok": true, "hits": hits, "kills": kills}

## 锁定：相机准星前方 aimRadius 内最近敌人，且距施法者 ≤ maxRange
func _acquire_target() -> Node3D:
	var cam: Camera3D = null
	for c in _caster.get_children():
		if c is Camera3D:
			cam = c
			break
	if cam == null:
		return null
	var origin := cam.global_position
	var aim_point := origin - cam.global_transform.basis.z * 5.0
	var aim_radius := float(_effect.get("aim_radius_m", 2.8))
	var max_range := float(_effect.get("max_range_m", 8.4))
	var best: Node3D = null
	var best_d := INF
	for c in _scene_root.get_children():
		if c == null or c == _caster or not c.has_method("take_damage") or String(c.name) == "Player":
			continue
		var p: Vector3 = c.global_position
		var d_aim := p.distance_to(aim_point)
		if d_aim > aim_radius:
			continue
		if p.distance_to(_caster.global_position) > max_range:
			continue
		if d_aim < best_d:
			best_d = d_aim
			best = c
	return best

func _nearest_hostile(from: Vector3, range_m: float, exclude: Array) -> Node3D:
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

## ---------- 闪电链特效（软点链：蓝紫辉光 ADD 外层 + 白蓝内芯，施法端粗→目标端细） ----------

func _lightning_bolt(from: Vector3, to: Vector3) -> void:
	var node := Node3D.new()
	_add_to_root(node)
	node.position = from
	var segs := maxi(4, int(_effect.get("segments", 10)))
	var jitter := float(_effect.get("jitter", 0.09))
	var dist := (to - from).length()
	var amp := maxf(0.15, dist * jitter)
	var n := (to - from).cross(Vector3.UP)
	if n.length() < 0.001:
		n = Vector3.RIGHT
	n = n.normalized()
	var pts: Array[Vector3] = [Vector3.ZERO]
	for i in range(1, segs):
		var t := float(i) / float(segs)
		var off := (randf() * 2.0 - 1.0) * amp
		pts.append((to - from) * t + n * off)
	pts.append(to - from)
	var smooth := _smooth_chain(pts, 2)
	var chain := _resample(smooth, 0.07)
	var dots: Array = []
	var n_pts := chain.size()
	for i in n_pts:
		var t := float(i) / float(maxi(1, n_pts - 1))
		var s := randf_range(0.75, 1.25)
		var r_out := lerpf(0.16, 0.045, t) * s
		dots.append(_bolt_dot(node, chain[i], r_out, Color(0.42, 0.28, 1.0, 0.3)))
		dots.append(_bolt_dot(node, chain[i], r_out * 0.38, Color(0.88, 0.86, 1.0, 0.9)))
	# 定格 duration_s 后线性淡出 fade_ms
	var tw := node.create_tween()
	tw.tween_interval(float(_effect.get("duration_s", 0.5)))
	tw.tween_method(func(v: float) -> void:
		for d in dots:
			var m := (d as Sprite3D).material_override as StandardMaterial3D
			var c: Color = m.albedo_color
			c.a = c.a * v
			m.albedo_color = c
		, 1.0, 0.0, float(_effect.get("fade_ms", 250.0)) / 1000.0)
	tw.tween_callback(func() -> void: node.queue_free())

func _bolt_dot(parent: Node3D, local_pos: Vector3, radius: float, color: Color) -> Sprite3D:
	var sp := Sprite3D.new()
	sp.texture = _dot_tex()
	sp.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	sp.pixel_size = 0.0025
	sp.position = local_pos
	# 软点贴图 64px，pixel_size 0.0025 → 基础尺寸 0.16m；scale = radius / 0.16
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

func _smooth_chain(pts: Array[Vector3], passes: int) -> Array[Vector3]:
	var cur := pts
	for _p in passes:
		var dense: Array[Vector3] = [cur[0]]
		for i in range(1, cur.size()):
			dense.append((cur[i - 1] + cur[i]) * 0.5)
			dense.append(cur[i])
		var out: Array[Vector3] = [dense[0]]
		for i in range(1, dense.size() - 1):
			out.append(dense[i - 1] * 0.25 + dense[i] * 0.5 + dense[i + 1] * 0.25)
		out.append(dense[dense.size() - 1])
		cur = out
	return cur

func _resample(pts: Array[Vector3], step: float) -> Array[Vector3]:
	var out: Array[Vector3] = []
	var acc := 0.0
	for i in range(pts.size() - 1):
		var p1 := pts[i]
		var p2 := pts[i + 1]
		var seg_len := p1.distance_to(p2)
		if seg_len < 1e-5:
			continue
		var t := acc / seg_len
		while t <= 1.0:
			out.append(p1.lerp(p2, t))
			acc += step
			t = acc / seg_len
		acc -= seg_len
	out.append(pts[pts.size() - 1])
	return out

## ---------- 命中爆炸（蓝紫冲击波 + 白紫粒子，旧版 _spawnImpact 配色） ----------

func _impact_bolt(pos: Vector3, decay_mul: float) -> void:
	var scale := 0.75 + 0.25 * decay_mul
	var ring := MeshInstance3D.new()
	var torus := TorusMesh.new()
	var r := 0.55 * scale
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
	# 白粒爆闪
	_bolt_burst(pos, 16, 1.2, 3.6, Color(1.0, 1.0, 1.0, 0.95), Color(0.94, 0.91, 1.0, 0.0), 0.5)
	# 紫粒外扩
	_bolt_burst(pos, 24, 0.9, 3.0, Color(0.79, 0.63, 1.0, 0.9), Color(0.42, 0.29, 1.0, 0.0), 0.7)

func _bolt_burst(pos: Vector3, amount: int, v_min: float, v_max: float, c0: Color, c1: Color, life: float) -> void:
	var p := GPUParticles3D.new()
	p.one_shot = true
	p.emitting = true
	p.amount = amount
	p.lifetime = life
	p.local_coords = false
	p.position = pos
	p.draw_pass_1 = _dot_pass(0.3, true)
	var pm := ParticleProcessMaterial.new()
	pm.direction = Vector3.ZERO
	pm.spread = 180.0
	pm.initial_velocity_min = v_min
	pm.initial_velocity_max = v_max
	pm.gravity = Vector3(0, -1.0, 0)
	pm.scale_min = 0.28
	pm.scale_max = 0.5
	pm.scale_curve = _grow_texture(0.5, 1.1)
	pm.color_ramp = _ramp([c0, c1], [0.0, 1.0])
	p.process_material = pm
	_add_to_root(p)
	_delayed_free(p, life + 0.3)

func _play_cast_sound() -> void:
	for path in CAST_SOUNDS:
		if not ResourceLoader.exists(path):
			continue
		var player := AudioStreamPlayer3D.new()
		player.stream = load(path)
		player.position = _caster.global_position
		player.max_distance = 50.0
		_add_to_root(player)
		player.play()
		_delayed_free(player, 3.0)

## ---------- 共用特效工具（与 fireball.gd 一致的软边粒子配方） ----------

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

func _grow_curve(from: float, to: float) -> Curve:
	var c := Curve.new()
	c.add_point(Vector2(0, from))
	c.add_point(Vector2(0.5, from + (to - from) * 0.6))
	c.add_point(Vector2(1, to))
	return c

func _grow_texture(from: float, to: float) -> CurveTexture:
	var tex := CurveTexture.new()
	tex.curve = _grow_curve(from, to)
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
