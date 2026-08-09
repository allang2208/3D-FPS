extends Node3D
## 火球（技能迁徙，从旧版 fireball-system.js / BoltSkillSystem 移植）
## 二段式（原版流程改良）：第一次释放 → 凝聚火球悬浮于左手握持位（73 帧动画，30s 内有效）；
## 第二次释放 → 朝瞄准方向投掷 → 命中/到射程 → 范围爆炸。
## 视觉按原版逐层迁移：
## - 73 帧火球贴图动画（fireball_spritesheet.png，hover 100ms / fly 50ms，billboard 面向相机）
## - 飞行尾迹：ADD 橙粒子，50ms 间隔（世界空间，跟随火球）
## - 爆炸三层：冲击波扩散圈（420ms 闪烁淡出）+ 火焰爆发（26 粒 ADD）+ 烟尘（8 粒放大淡出）
## - 命中音效（skills.json fireball.sounds.hit）
## 伤害 = floor(damageBase + matk*magicMul + int*intMul)，AOE 距离衰减 damage*(0.5+0.5*(1-d/r))

const HIT_MASK := 3  # 1 墙体 + 2 敌人
const PX_TO_M := 0.014
const FIREBALL_SHADER := "res://assets/shaders/fireball.gdshader"
const HIT_SOUND := "res://assets/sfx/fireball.mp3"

signal consumed

var _dir := Vector3.FORWARD
var _speed := 22.4
var _max_range := 16.8
var _radius := 1.19
var _damage := 90
var _traveled := 0.0
var _scene_root: Node
var _age := 0.0
var _hovering := false
var _caster: Node3D
var _hover_t := 0.0
var _hover_duration := 30.0
var _consumed_emitted := false
var _trail: GPUParticles3D
var _trail_white: GPUParticles3D
static var _dot_tex_cache: Texture2D

static func fire(scene_root: Node, origin: Vector3, dir: Vector3, level: int, matk: int, intt: int) -> Node3D:
	var script := load("res://scripts/fireball.gd")
	var fb: Node3D = script.new()
	fb.configure(origin, dir, level, matk, intt, scene_root)
	scene_root.add_child(fb)
	fb.build_visual()
	return fb

## 第一段：凝聚火球（绕施法者环绕，等玩家第二次释放投掷）
static func spawn_hover(scene_root: Node, caster: Node3D, level: int, matk: int, intt: int) -> Node3D:
	var script := load("res://scripts/fireball.gd")
	var fb: Node3D = script.new()
	fb.configure(caster.global_position + Vector3(0, 1.2, 0), Vector3.FORWARD, level, matk, intt, scene_root)
	scene_root.add_child(fb)
	fb.build_visual()
	fb.enter_hover(caster)
	return fb

func configure(origin: Vector3, dir: Vector3, level: int, matk: int, intt: int, scene_root: Node) -> void:
	_damage = floori(80 + level * 10 + matk * (2.0 + 0.5 * level) + intt * (2.5 + 0.75 * level))
	_radius = (80 + level * 5) * PX_TO_M
	_speed = 1600.0 * PX_TO_M
	_max_range = 1200.0 * PX_TO_M
	_dir = dir.normalized()
	_scene_root = scene_root
	position = origin

func build_visual() -> void:
	# 本体（D 方案）：程序化火焰 shader 球体
	var sphere := MeshInstance3D.new()
	var sm := SphereMesh.new()
	sm.radius = 0.16
	sm.height = 0.32
	sm.radial_segments = 24
	sm.rings = 16
	var shader: Shader = load(FIREBALL_SHADER)
	var smat := ShaderMaterial.new()
	smat.shader = shader
	sm.material = smat
	sphere.mesh = sm
	add_child(sphere)
	# 柔和光晕（软边圆点贴图 + ADD，遮住贴图边缘像素化）
	var glow := Sprite3D.new()
	glow.texture = _dot_tex()
	glow.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	glow.pixel_size = 0.0025
	glow.scale = Vector3(2.6, 2.6, 1.0)
	var glow_mat := StandardMaterial3D.new()
	glow_mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	glow_mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	glow_mat.blend_mode = BaseMaterial3D.BLEND_MODE_ADD
	glow_mat.albedo_texture = _dot_tex()
	glow_mat.albedo_color = Color(1.0, 0.55, 0.2, 0.32)
	glow.material_override = glow_mat
	add_child(glow)
	# 橙色点光（火球照亮周围）
	var light := OmniLight3D.new()
	light.light_color = Color(1.0, 0.5, 0.2)
	light.light_energy = 2.5
	light.omni_range = 5.0
	add_child(light)
	# 常驻火焰层一：白色核心——从球面喷涌的白热火舌（燃烧中心）
	var flame_white := GPUParticles3D.new()
	flame_white.emitting = true
	flame_white.one_shot = false
	flame_white.amount = 26
	flame_white.lifetime = 0.55
	flame_white.local_coords = false
	flame_white.draw_pass_1 = _dot_pass(0.5, true)
	var wp := ParticleProcessMaterial.new()
	wp.direction = Vector3.UP
	wp.spread = 55.0
	wp.emission_shape = ParticleProcessMaterial.EMISSION_SHAPE_SPHERE
	wp.emission_sphere_radius = 0.14
	wp.initial_velocity_min = 0.3
	wp.initial_velocity_max = 0.7
	wp.gravity = Vector3(0, 0.6, 0)
	wp.scale_min = 0.28
	wp.scale_max = 0.5
	wp.scale_curve = _grow_texture(0.5, 1.0)
	wp.color_ramp = _ramp([
		Color(1.0, 1.0, 1.0, 0.7),
		Color(1.0, 0.95, 0.72, 0.6),
		Color(1.0, 0.7, 0.3, 0.0),
	], [0.0, 0.3, 1.0])
	flame_white.process_material = wp
	add_child(flame_white)
	# 常驻火焰层二：黄色主焰——向上窜的火舌主体，带翻涌扭曲（燃烧火苗）
	var flame_yellow := GPUParticles3D.new()
	flame_yellow.emitting = true
	flame_yellow.one_shot = false
	flame_yellow.amount = 40
	flame_yellow.lifetime = 0.8
	flame_yellow.local_coords = false
	flame_yellow.draw_pass_1 = _dot_pass(0.6, true)
	var yp := ParticleProcessMaterial.new()
	yp.direction = Vector3.UP
	yp.spread = 40.0
	yp.emission_shape = ParticleProcessMaterial.EMISSION_SHAPE_SPHERE
	yp.emission_sphere_radius = 0.15
	yp.initial_velocity_min = 0.5
	yp.initial_velocity_max = 1.1
	yp.gravity = Vector3(0, 0.5, 0)
	yp.scale_min = 0.4
	yp.scale_max = 0.75
	yp.scale_curve = _grow_texture(0.6, 1.2)
	yp.turbulence_enabled = true
	yp.turbulence_noise_strength = 1.1
	yp.turbulence_noise_scale = 5.0
	yp.turbulence_noise_speed = Vector3(1.5, 1.5, 1.5)
	yp.color_ramp = _ramp([
		Color(1.0, 0.95, 0.62, 0.6),
		Color(1.0, 0.82, 0.3, 0.5),
		Color(1.0, 0.45, 0.1, 0.1),
		Color(1.0, 0.3, 0.05, 0.0),
	], [0.0, 0.25, 0.55, 1.0])
	flame_yellow.process_material = yp
	add_child(flame_yellow)
	# 飞行尾迹（原版 trail：ADD 橙粒子，世界空间跟随，仅飞行时开启）
	var trail := GPUParticles3D.new()
	trail.emitting = false  # 飞行时才开，悬浮时避免垂直拖尾
	trail.one_shot = false
	trail.amount = 90
	trail.lifetime = 0.6
	trail.local_coords = false
	trail.draw_pass_1 = _dot_pass(0.45, true)
	var tp := ParticleProcessMaterial.new()
	tp.direction = Vector3.ZERO
	tp.spread = 180.0
	tp.initial_velocity_min = 0.05
	tp.initial_velocity_max = 0.5
	tp.gravity = Vector3(0, -0.4, 0)
	tp.scale_min = 0.4
	tp.scale_max = 0.7
	tp.color_ramp = _ramp([
		Color(1.0, 0.75, 0.3, 0.8),
		Color(1.0, 0.35, 0.1, 0.0),
	], [0.0, 1.0])
	trail.process_material = tp
	add_child(trail)
	_trail = trail
	# 飞行白热核心尾迹（更亮更小，紧贴弹道）
	var trail_white := GPUParticles3D.new()
	trail_white.emitting = false
	trail_white.one_shot = false
	trail_white.amount = 40
	trail_white.lifetime = 0.3
	trail_white.local_coords = false
	trail_white.draw_pass_1 = _dot_pass(0.3, true)
	var twp := ParticleProcessMaterial.new()
	twp.direction = Vector3.ZERO
	twp.spread = 60.0
	twp.initial_velocity_min = 0.02
	twp.initial_velocity_max = 0.15
	twp.gravity = Vector3(0, -0.2, 0)
	twp.scale_min = 0.35
	twp.scale_max = 0.55
	twp.color_ramp = _ramp([
		Color(1.0, 0.95, 0.7, 0.9),
		Color(1.0, 0.6, 0.2, 0.0),
	], [0.0, 1.0])
	trail_white.process_material = twp
	add_child(trail_white)
	_trail_white = trail_white
	# 常驻火焰层三：橙色外焰——更大更淡，向上飘散形成火苗轮廓
	var flame_orange := GPUParticles3D.new()
	flame_orange.emitting = true
	flame_orange.one_shot = false
	flame_orange.amount = 32
	flame_orange.lifetime = 0.9
	flame_orange.local_coords = false
	flame_orange.draw_pass_1 = _dot_pass(0.6, true)
	var op := ParticleProcessMaterial.new()
	op.direction = Vector3.UP
	op.spread = 75.0
	op.emission_shape = ParticleProcessMaterial.EMISSION_SHAPE_SPHERE
	op.emission_sphere_radius = 0.13
	op.initial_velocity_min = 0.25
	op.initial_velocity_max = 0.6
	op.gravity = Vector3(0, 0.3, 0)
	op.scale_min = 0.4
	op.scale_max = 0.75
	op.scale_curve = _grow_texture(0.7, 1.3)
	op.color_ramp = _ramp([
		Color(1.0, 0.65, 0.2, 0.45),
		Color(1.0, 0.4, 0.1, 0.1),
		Color(1.0, 0.3, 0.05, 0.0),
	], [0.0, 0.45, 1.0])
	flame_orange.process_material = op
	add_child(flame_orange)

## 第一段：凝聚（火球悬浮于左手位置——相机前下方偏左，镜像枪械握持位）
func enter_hover(caster: Node3D) -> void:
	_hovering = true
	_caster = caster
	_age = 0.0
	_hover_t = 0.0
	if _trail != null:
		_trail.emitting = false
	if _trail_white != null:
		_trail_white.emitting = false

## 第二段：发射（原版 _launchAll：从当前轨道位置起飞，动画切 20fps）
func launch(dir: Vector3) -> void:
	if not _hovering:
		return
	_hovering = false
	_dir = dir.normalized()
	_age = 0.0
	if _trail != null:
		_trail.emitting = true
	if _trail_white != null:
		_trail_white.emitting = true

func _physics_process(delta: float) -> void:
	if _hovering:
		_hover_age(delta)
		return
	_age += delta
	if _age >= 3.0 or _traveled >= _max_range:
		_explode(global_position)
		return
	var step := _speed * delta
	var from := global_position
	var to := from + _dir * step
	var query := PhysicsRayQueryParameters3D.create(from, to, HIT_MASK)
	var hit := get_world_3d().direct_space_state.intersect_ray(query)
	if hit:
		_explode(hit.position)
		return
	global_position = to
	_traveled += step

func _hover_age(delta: float) -> void:
	_age += delta
	_hover_t += delta
	if _age >= _hover_duration:
		_emit_consumed()
		queue_free()
		return
	if _caster == null or not is_instance_valid(_caster):
		_emit_consumed()
		queue_free()
		return
	# 左手握持位：相机前下方偏左（与枪械握持位镜像），轻微上下浮动
	var cam := _caster.get_node_or_null("Camera3D") as Camera3D
	if cam != null:
		var b := cam.global_transform.basis
		var hold := cam.global_position + b * Vector3(-0.28, -0.24, -0.85)
		hold.y += sin(_hover_t * 2.2) * 0.03
		global_position = hold
	else:
		global_position = _caster.global_position + Vector3(0, 1.35, -0.4)

func _emit_consumed() -> void:
	if not _consumed_emitted:
		_consumed_emitted = true
		consumed.emit()

## ---------- 爆炸（三层特效 + 音效 + AOE 伤害，原版顺序） ----------

func _explode(pos: Vector3) -> void:
	global_position = pos
	_shockwave_ring(pos)
	_flame_burst(pos)
	_smoke(pos)
	_play_hit_sound(pos)
	_aoe_damage(pos)
	_emit_consumed()
	queue_free()

func _aoe_damage(pos: Vector3) -> void:
	var scene_root: Node = _scene_root if _scene_root != null else get_tree().current_scene
	if scene_root == null:
		return
	for c in scene_root.get_children():
		if c != null and c.has_method("take_damage") and String(c.name) != "Player":
			var dist: float = (c.global_position - pos).length()
			if dist <= _radius:
				var ratio := 1.0 - clampf(dist / _radius, 0.0, 1.0)
				var dmg := maxi(1, floori(_damage * (0.5 + 0.5 * ratio)))
				c.take_damage(dmg)

func _shockwave_ring(pos: Vector3) -> void:
	var ring := MeshInstance3D.new()
	var torus := TorusMesh.new()
	torus.inner_radius = _radius * 0.92
	torus.outer_radius = _radius
	torus.rings = 16
	var mat := StandardMaterial3D.new()
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	mat.blend_mode = BaseMaterial3D.BLEND_MODE_ADD
	mat.albedo_color = Color(1.0, 0.44, 0.13, 0.9)
	torus.material = mat
	ring.mesh = torus
	ring.rotation_degrees = Vector3(90, 0, 0)
	ring.position = pos
	ring.scale = Vector3.ONE * 0.01
	_add_to_root(ring)
	# 0→半径扩散 + 闪烁（0.55+0.45*sin(t*π*8)）+ 淡出（原版 fireGroundShockwave 420ms cubic easeOut）
	var tw := ring.create_tween()
	tw.tween_method(func(t: float) -> void:
		ring.scale = Vector3.ONE * maxf(0.01, t)
		var flick: float = 0.55 + 0.45 * sin(t * TAU * 4.0)
		mat.albedo_color.a = (1.0 - t) * 0.9 * flick
		, 0.0, 1.0, 0.42).set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_OUT)
	tw.tween_callback(func() -> void: ring.queue_free())

func _flame_burst(pos: Vector3) -> void:
	var boom := GPUParticles3D.new()
	boom.one_shot = true
	boom.emitting = true
	boom.amount = 26
	boom.lifetime = 0.5
	boom.local_coords = false
	boom.position = pos
	boom.draw_pass_1 = _dot_pass(0.3, true)
	var pm := ParticleProcessMaterial.new()
	pm.direction = Vector3.ZERO
	pm.spread = 180.0
	pm.initial_velocity_min = 1.7
	pm.initial_velocity_max = 5.9
	pm.gravity = Vector3(0, -1.0, 0)
	pm.scale_min = 0.12
	pm.scale_max = 0.3
	pm.color_ramp = _ramp([
		Color(1.0, 1.0, 1.0, 0.9),
		Color(1.0, 0.82, 0.48, 0.8),
		Color(1.0, 0.53, 0.19, 0.6),
		Color(1.0, 0.33, 0.06, 0.0),
	], [0.0, 0.35, 0.7, 1.0])
	boom.process_material = pm
	_add_to_root(boom)
	_delayed_free(boom, 0.8)

func _smoke(pos: Vector3) -> void:
	var smoke := GPUParticles3D.new()
	smoke.one_shot = true
	smoke.emitting = true
	smoke.amount = 8
	smoke.lifetime = 1.0
	smoke.local_coords = false
	smoke.position = pos
	smoke.draw_pass_1 = _dot_pass(0.4, false)
	var pm := ParticleProcessMaterial.new()
	pm.direction = Vector3.ZERO
	pm.spread = 180.0
	pm.initial_velocity_min = 0.3
	pm.initial_velocity_max = 1.0
	pm.gravity = Vector3(0, 0.4, 0)
	pm.scale_min = 0.2
	pm.scale_max = 0.35
	pm.color_ramp = _ramp([
		Color(0.33, 0.33, 0.33, 0.35),
		Color(0.33, 0.33, 0.33, 0.0),
	], [0.0, 1.0])
	smoke.process_material = pm
	_add_to_root(smoke)
	_delayed_free(smoke, 1.3)

func _play_hit_sound(pos: Vector3) -> void:
	if not ResourceLoader.exists(HIT_SOUND):
		return
	var player := AudioStreamPlayer3D.new()
	player.stream = load(HIT_SOUND)
	player.position = pos
	player.max_distance = 40.0
	_add_to_root(player)
	player.play()
	_delayed_free(player, 3.0)

func _add_to_root(node: Node) -> void:
	var root: Node = _scene_root if _scene_root != null else get_tree().current_scene
	if root != null:
		root.add_child(node)
	else:
		get_parent().add_child(node)

func _delayed_free(node: Node, delay: float) -> void:
	var t := node.get_tree().create_timer(delay)
	t.timeout.connect(func() -> void: node.queue_free())

## 软边圆点粒子贴图（等价 Phaser impact_dot：径向渐隐，消除硬边方块）
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

## 粒子生长曲线：随时间从 from 线性增长到 to（火焰越往上越宽）
func _grow_curve(from: float, to: float) -> Curve:
	var c := Curve.new()
	c.add_point(Vector2(0, from))
	c.add_point(Vector2(0.5, from + (to - from) * 0.6))
	c.add_point(Vector2(1, to))
	return c

## 将生长曲线包成 CurveTexture（Godot 4 的 scale_curve 属性类型）
func _grow_texture(from: float, to: float) -> CurveTexture:
	var tex := CurveTexture.new()
	tex.curve = _grow_curve(from, to)
	return tex
