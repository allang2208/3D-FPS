extends Node3D
## 火球（技能迁徙，从旧版 fireball-system.js / BoltSkillSystem 移植）
## 朝方向直线飞行，命中墙体/敌人或到达最大射程后范围爆炸：
## 伤害 = floor(damageBase + matk*magicMul + int*intMul)，AOE 距离衰减 damage*(0.5+0.5*(1-d/r))
## 旧版像素换算：1px ≈ 0.014m（flySpeed 1600px/s→22.4m/s、maxRange 1200px→16.8m、
## explosionRadius 85px→1.19m）。

const HIT_MASK := 3  # 1 墙体 + 2 敌人
const PX_TO_M := 0.014

var _dir := Vector3.FORWARD
var _speed := 22.4
var _max_range := 16.8
var _radius := 1.19
var _damage := 90
var _traveled := 0.0
var _scene_root: Node
var _age := 0.0

static func fire(scene_root: Node, origin: Vector3, dir: Vector3, level: int, matk: int, intt: int) -> Node3D:
	var script := load("res://scripts/fireball.gd")
	var fb: Node3D = script.new()
	fb.configure(origin, dir, level, matk, intt, scene_root)
	scene_root.add_child(fb)
	fb.build_visual()
	return fb

func configure(origin: Vector3, dir: Vector3, level: int, matk: int, intt: int, scene_root: Node) -> void:
	# 旧版公式（skills.json fireball effectFormula，等级 1 起步）
	_damage = floori(80 + level * 10 + matk * (2.0 + 0.5 * level) + intt * (2.5 + 0.75 * level))
	var radius_px := 80 + level * 5
	_radius = radius_px * PX_TO_M
	_speed = 1600.0 * PX_TO_M
	_max_range = 1200.0 * PX_TO_M
	_dir = dir.normalized()
	_scene_root = scene_root
	position = origin

func build_visual() -> void:
	var sphere := MeshInstance3D.new()
	var sm := SphereMesh.new()
	sm.radius = 0.16
	sm.height = 0.32
	var mat := StandardMaterial3D.new()
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	mat.albedo_color = Color(1.0, 0.75, 0.35)
	mat.emission_enabled = true
	mat.emission = Color(1.0, 0.45, 0.15) * 2.0
	sm.material = mat
	sphere.mesh = sm
	add_child(sphere)
	# 飞行尾迹
	var trail := GPUParticles3D.new()
	trail.one_shot = false
	trail.emitting = true
	trail.amount = 24
	trail.lifetime = 0.3
	trail.local_coords = true
	trail.process_material = _particle_mat(Vector3(0, 0, 0), 1.0, 0.2, 0.12, Color(1.0, 0.6, 0.2, 0.7))
	trail.position = Vector3(0, 0, -0.25)
	add_child(trail)

func _physics_process(delta: float) -> void:
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
	rotate_y(delta * 6.0)

func _explode(pos: Vector3) -> void:
	global_position = pos
	# 爆炸粒子
	var boom := GPUParticles3D.new()
	boom.one_shot = true
	boom.emitting = true
	boom.amount = 26
	boom.lifetime = 0.5
	boom.local_coords = false
	boom.process_material = _particle_mat(Vector3(0, 0, 0), 4.0, 0.3, 0.15, Color(1.0, 0.5, 0.2, 1.0))
	boom.position = pos
	var scene_root: Node = _scene_root if _scene_root != null else get_tree().current_scene
	scene_root.add_child(boom)
	# AOE 伤害（距离衰减，旧版 _explodeAoE）
	if scene_root != null:
		for c in scene_root.get_children():
			if c != null and c.has_method("take_damage") and String(c.name) != "Player":
				var dist: float = (c.global_position - pos).length()
				if dist <= _radius:
					var ratio := 1.0 - clampf(dist / _radius, 0.0, 1.0)
					var dmg := maxi(1, floori(_damage * (0.5 + 0.5 * ratio)))
					c.take_damage(dmg)
	queue_free()

func _particle_mat(dir: Vector3, speed: float, scale_s: float, scale_e: float, tint: Color) -> ParticleProcessMaterial:
	var pm := ParticleProcessMaterial.new()
	pm.direction = dir
	pm.spread = 180.0
	pm.initial_velocity_min = speed * 0.4
	pm.initial_velocity_max = speed
	pm.gravity = Vector3(0, -2.0, 0)
	pm.scale_min = scale_s
	pm.scale_max = scale_s * 1.4
	pm.color = tint
	return pm
