extends Node3D
## 冰锥技能（两段式迁移，旧版 IceSpikeSystem / skills.json iceSpike）
## 第一段：N 颗冰锥悬浮环绕施法者（水平椭圆 + 垂直高度分层，错速环绕）
## 第二段：全部朝瞄准方向齐射 → 命中/撞墙 = 碎裂（冰屑 + 小冰环 + 音效节流）
## 到达最大射程 = 静默消失（无特效）。命中判定走射线，与视觉分离。

const PX_TO_M := 0.014
const HIT_MASK := 3  # 1 墙体 + 2 敌人
const HIT_SOUND := "res://assets/sfx/ice.mp3"
## 原版冰锥贴图池：每次施法每颗随机一张（旧版 ICE_SPIKE_TEXES 4 张）
## 注：billboard 模式会忽略 Sprite3D 的 rotation（实测 4.7 无效），故用预旋转好的横向贴图
const ICE_TEXES := [
	"res://assets/ui/icons/skills/ice_spike_h_01.png",
	"res://assets/ui/icons/skills/ice_spike_h_02.png",
	"res://assets/ui/icons/skills/ice_spike_h_03.png",
	"res://assets/ui/icons/skills/ice_spike_h_04.png",
]

signal consumed
signal cast_finished(hits, kills)

var _spike_count := 2
var _damage := 30
var _speed := 22.4
var _max_range := 11.2
var _scene_root: Node
var _caster: Node3D
var _hovering := false
var _hover_t := 0.0
var _hover_duration := 30.0
var _consumed_emitted := false
var _hits := 0
var _kills := 0
var _hit_sound_cd := 0.0
var _spikes: Array = []
static var _dot_tex_cache: Texture2D

## 第一段：凝聚 N 颗冰锥环绕施法者
static func spawn_hover(scene_root: Node, caster: Node3D, level: int, matk: int, intt: int, spike_count: int) -> Node3D:
	var script := load("res://scripts/ice_spike.gd")
	var ic: Node3D = script.new()
	ic.configure(level, matk, intt, spike_count, scene_root)
	scene_root.add_child(ic)
	ic.build_visual()
	ic.enter_hover(caster)
	return ic

func configure(level: int, matk: int, intt: int, spike_count: int, scene_root: Node) -> void:
	_damage = floori(30 + level * 5 + matk * (1.2 + 0.25 * level) + intt * (1.2 + 0.25 * level))
	_spike_count = maxi(1, spike_count)
	_speed = 1600.0 * PX_TO_M
	_max_range = 800.0 * PX_TO_M
	_scene_root = scene_root

func build_visual() -> void:
	# 无本体视觉；冰锥个体由 _spawn_spikes 创建
	pass

func enter_hover(caster: Node3D) -> void:
	_hovering = true
	_caster = caster
	_hover_t = 0.0
	_spawn_spikes()

func _spawn_spikes() -> void:
	# 前方扇形松散分布（3D 第一人称优化）：x 水平散开、y 上下错开、z 前后错开，
	# 每颗独立浮动相位/频率——像法术凝聚时冰锥在面前蓄势漂浮，避免死板转圈
	for i in _spike_count:
		var t := float(i) / float(maxi(1, _spike_count - 1))
		var bx := lerpf(-0.55, 0.55, t) + (randf() - 0.5) * 0.12
		var by := lerpf(-0.18, 0.1, t) + (randf() - 0.5) * 0.08
		var bz := lerpf(0.48, 0.72, float(i % 2)) + (randf() - 0.5) * 0.12
		_spikes.append(_make_spike(i, Vector3(bx, by, -bz), randf_range(0.6, 1.4),
			randf_range(1.8, 2.6), randf_range(0.8, 1.3), randf_range(1.0, 1.6)))

func _make_spike(i: int, base: Vector3, amp: float, freq_a: float, freq_b: float, freq_c: float) -> Dictionary:
	var node := Node3D.new()
	# 本体：3D 冰锥（锥体横置，尖端朝 -Z）——尖端可随 node 直对瞄准方向
	var mi := MeshInstance3D.new()
	var cyl := CylinderMesh.new()
	cyl.top_radius = 0.015
	cyl.bottom_radius = 0.04
	cyl.height = 0.3
	cyl.radial_segments = 8
	mi.rotation_degrees = Vector3(-90, 0, 0)  # 横置：尖端（细端）朝 -Z（look_at 方向）
	var cmat := StandardMaterial3D.new()
	cmat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	cmat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	cmat.albedo_color = Color(0.75, 0.92, 1.0, 0.92)
	cmat.emission_enabled = true
	cmat.emission = Color(0.5, 0.8, 1.0)
	cmat.emission_energy_multiplier = 1.5
	cyl.material = cmat
	mi.mesh = cyl
	node.add_child(mi)
	# 冰蓝光晕（软点 ADD，让冰锥有"法光"感）
	var glow := Sprite3D.new()
	glow.texture = _dot_tex()
	glow.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	glow.pixel_size = 0.0025
	glow.scale = Vector3(1.8, 1.8, 1.0)
	var gm := StandardMaterial3D.new()
	gm.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	gm.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	gm.blend_mode = BaseMaterial3D.BLEND_MODE_ADD
	gm.albedo_texture = _dot_tex()
	gm.albedo_color = Color(0.6, 0.85, 1.0, 0.35)
	glow.material_override = gm
	node.add_child(glow)
	# 大寒气光晕（柔和蓝白光雾，参考火球 glow——无颗粒/边角，只有渐变光）
	var haze := Sprite3D.new()
	haze.texture = _dot_tex()
	haze.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	haze.pixel_size = 0.0025
	haze.scale = Vector3(2.8, 2.8, 1.0)
	var hm := StandardMaterial3D.new()
	hm.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	hm.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	hm.blend_mode = BaseMaterial3D.BLEND_MODE_ADD
	hm.albedo_texture = _dot_tex()
	hm.albedo_color = Color(0.72, 0.9, 1.0, 0.2)
	haze.material_override = hm
	node.add_child(haze)
	# 飞行尾迹（柔和寒气拖尾：大软点 + 蓝白低透明渐隐，仅飞行时开启）
	var trail := GPUParticles3D.new()
	trail.emitting = false
	trail.one_shot = false
	trail.amount = 10
	trail.lifetime = 0.4
	trail.local_coords = false
	trail.draw_pass_1 = _dot_pass(0.3, true)
	var tp := ParticleProcessMaterial.new()
	tp.direction = Vector3.ZERO
	tp.spread = 180.0
	tp.initial_velocity_min = 0.0
	tp.initial_velocity_max = 0.18
	tp.gravity = Vector3(0, -0.2, 0)
	tp.scale_min = 0.55
	tp.scale_max = 0.85
	tp.scale_curve = _grow_texture(1.0, 0.4)  # 柔和放大后渐隐，无小碎粒
	tp.color_ramp = _ramp([
		Color(0.95, 0.98, 1.0, 0.4),
		Color(0.72, 0.9, 1.0, 0.18),
		Color(0.5, 0.75, 1.0, 0.0),
	], [0.0, 0.45, 1.0])
	trail.process_material = tp
	node.add_child(trail)
	add_child(node)
	return {"node": node, "i": i, "base": base, "amp": amp,
		"freq_a": freq_a, "freq_b": freq_b, "freq_c": freq_c,
		"launched": false, "dir": Vector3.FORWARD, "traveled": 0.0, "trail": trail, "done": false}

## 第二段：齐射
func launch(dir: Vector3) -> void:
	if not _hovering:
		return
	_hovering = false
	# 汇聚点：相机前方 5m、躯干高度（避免冰锥从敌人头顶水平掠过）
	var cam: Camera3D = null
	for c in _caster.get_children():
		if c is Camera3D:
			cam = c
			break
	# 发射：直接沿瞄准方向平行投掷（不汇聚到一点）
	var fire_dir := dir.normalized()
	for s in _spikes:
		var p: Vector3 = s.node.global_position
		p.y = 0.8  # 对齐躯干高度，避免从敌人头顶掠过
		s.node.global_position = p
		s.launched = true
		s.dir = fire_dir
		s.traveled = 0.0
		s.trail.emitting = true

func _physics_process(delta: float) -> void:
	if _hovering:
		_hover_update(delta)
		return
	_fly_update(delta)
	var all_done := true
	for s in _spikes:
		if not bool(s.done):
			all_done = false
			break
	if all_done:
		cast_finished.emit(_hits, _kills)
		_emit_consumed()
		queue_free()

func _hover_update(delta: float) -> void:
	_hover_t += delta
	if _hover_t >= _hover_duration or _caster == null or not is_instance_valid(_caster):
		_emit_consumed()
		queue_free()
		return
	var center := _caster.global_position
	var cam: Camera3D = null
	for c in _caster.get_children():
		if c is Camera3D:
			cam = c
			break
	if cam != null:
		center = cam.global_position
	var aim_dir := Vector3(0, 0, -5.0)
	if cam != null:
		aim_dir = cam.global_position - cam.global_transform.basis.z * 5.0
	for s in _spikes:
		var b: Vector3 = s.base
		# 各自相位浮动：上下/左右/前后独立频率（每颗像漂浮的冰晶，非死板转圈）
		var dx := sin(_hover_t * float(s.freq_b) + float(s.i) * 0.9) * 0.03
		var dy := sin(_hover_t * float(s.freq_a) + float(s.i) * 1.3) * 0.05
		var dz := sin(_hover_t * float(s.freq_c) + float(s.i) * 2.1) * 0.04
		var pos := center + Vector3(b.x + dx, b.y + dy, b.z + dz)
		s.node.global_position = pos
		# 朝向发射汇聚方向（贴图为 billboard 不随 node 旋转，look_at 供结构/未来 3D 元素）
		s.node.look_at(aim_dir, Vector3.UP)

func _fly_update(delta: float) -> void:
	_hit_sound_cd = maxf(0.0, _hit_sound_cd - delta)
	# 实时追踪准星瞄准点：每帧把冰锥方向指向准星所指，近距离也能精准打击
	var aim := _aim_point()
	for s in _spikes:
		if bool(s.done) or not bool(s.launched):
			continue
		var step := _speed * delta
		var from: Vector3 = s.node.global_position
		var dir_to_aim := (aim - from).normalized()
		if dir_to_aim.length() > 0.001:
			s.dir = dir_to_aim
		var to: Vector3 = from + (s.dir as Vector3) * step
		s.traveled += step
		if s.traveled >= _max_range:
			s.done = true
			s.node.visible = false
			s.trail.emitting = false
			continue
		var query := PhysicsRayQueryParameters3D.create(from, to, HIT_MASK)
		var hit := get_world_3d().direct_space_state.intersect_ray(query)
		if hit:
			_shatter(s, hit.position, hit.get("collider"))
			s.done = true
			continue
		s.node.global_position = to
		# 锥体尖端实时朝向当前飞行方向（准星方向）
		s.node.look_at(to + (s.dir as Vector3), Vector3.UP)

## 准星瞄准点：相机前方射线（HIT_MASK）命中点，否则前方 5m
func _aim_point() -> Vector3:
	var cam: Camera3D = null
	if _caster != null:
		for c in _caster.get_children():
			if c is Camera3D:
				cam = c
				break
	if cam == null:
		return _caster.global_position + Vector3(0, 0, -5.0)
	var origin := cam.global_position
	var fwd := -cam.global_transform.basis.z
	var query := PhysicsRayQueryParameters3D.create(origin, origin + fwd * _max_range, HIT_MASK)
	var hit := get_world_3d().direct_space_state.intersect_ray(query)
	if hit:
		return hit.position
	return origin + fwd * 5.0

## 命中/撞墙：碎裂（冰屑带重力 + 小冰环 + 音效节流）
func _shatter(s: Dictionary, pos: Vector3, collider: Object) -> void:
	s.node.visible = false
	s.trail.emitting = false
	_ice_shards(pos)
	_ice_ring(pos)
	_play_hit_sound(pos)
	if collider != null and collider.has_method("take_damage") and String(collider.name) != "Player":
		var was_alive := _hp_of(collider) > 0
		collider.take_damage(_damage)
		_hits += 1
		if was_alive and _hp_of(collider) <= 0:
			_kills += 1

func _ice_shards(pos: Vector3) -> void:
	var p := GPUParticles3D.new()
	p.one_shot = true
	p.emitting = true
	p.amount = 12
	p.lifetime = 0.45
	p.local_coords = false
	p.position = pos
	p.draw_pass_1 = _dot_pass(0.3, true)
	var pm := ParticleProcessMaterial.new()
	pm.direction = Vector3.ZERO
	pm.spread = 180.0
	pm.initial_velocity_min = 1.4
	pm.initial_velocity_max = 4.5
	pm.gravity = Vector3(0, -7.0, 0)
	pm.scale_min = 0.5
	pm.scale_max = 0.9
	pm.scale_curve = _grow_texture(1.0, 0.2)  # 旧版 scale 1.6→0.15 渐小
	pm.color_ramp = _ramp([
		Color(1.0, 1.0, 1.0, 0.9),
		Color(0.7, 0.9, 1.0, 0.5),
		Color(0.4, 0.65, 1.0, 0.0),
	], [0.0, 0.4, 1.0])
	p.process_material = pm
	_add_to_root(p)
	_delayed_free(p, 0.75)
	# 白色爆闪（旧版 tint 白打头，短促亮闪）
	var flash := GPUParticles3D.new()
	flash.one_shot = true
	flash.emitting = true
	flash.amount = 6
	flash.lifetime = 0.18
	flash.local_coords = false
	flash.position = pos
	flash.draw_pass_1 = _dot_pass(0.25, true)
	var fp := ParticleProcessMaterial.new()
	fp.direction = Vector3.ZERO
	fp.spread = 180.0
	fp.initial_velocity_min = 0.4
	fp.initial_velocity_max = 1.6
	fp.gravity = Vector3.ZERO
	fp.scale_min = 0.4
	fp.scale_max = 0.7
	fp.scale_curve = _grow_texture(1.0, 0.1)
	fp.color_ramp = _ramp([
		Color(1.0, 1.0, 1.0, 1.0),
		Color(0.85, 0.95, 1.0, 0.0),
	], [0.0, 1.0])
	flash.process_material = fp
	_add_to_root(flash)
	_delayed_free(flash, 0.4)

func _ice_ring(pos: Vector3) -> void:
	var ring := MeshInstance3D.new()
	var torus := TorusMesh.new()
	torus.inner_radius = 0.22
	torus.outer_radius = 0.32
	torus.rings = 14
	var mat := StandardMaterial3D.new()
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	mat.blend_mode = BaseMaterial3D.BLEND_MODE_ADD
	mat.albedo_color = Color(0.62, 0.85, 1.0, 0.8)
	torus.material = mat
	ring.mesh = torus
	ring.rotation_degrees = Vector3(90, 0, 0)
	ring.position = pos
	ring.scale = Vector3.ONE * 0.1
	_add_to_root(ring)
	var tw := ring.create_tween()
	tw.tween_method(func(t: float) -> void:
		ring.scale = Vector3.ONE * (0.1 + t * 0.9)
		var flick: float = 0.55 + 0.45 * sin(t * TAU * 4.0)  # 旧版 flicker
		mat.albedo_color.a = (1.0 - t) * 0.8 * flick
		, 0.0, 1.0, 0.32).set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_OUT)
	tw.tween_callback(func() -> void: ring.queue_free())

func _play_hit_sound(pos: Vector3) -> void:
	if _hit_sound_cd > 0.0 or not ResourceLoader.exists(HIT_SOUND):
		return
	_hit_sound_cd = 0.09  # 90ms 节流（旧版防同帧多颗刷音）
	var player := AudioStreamPlayer3D.new()
	player.stream = load(HIT_SOUND)
	player.position = pos
	player.max_distance = 40.0
	_add_to_root(player)
	player.play()
	_delayed_free(player, 3.0)

func _emit_consumed() -> void:
	if not _consumed_emitted:
		_consumed_emitted = true
		consumed.emit()

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
	m.vertex_color_use_as_albedo = true  # 粒子 color_ramp 生效的关键
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

func _hp_of(node: Object) -> int:
	var h = node.get("_hp")
	return int(h) if h != null else 0
