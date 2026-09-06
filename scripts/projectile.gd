class_name Projectile
extends Node3D
## 标准弹道飞行：子弹以恒定速度在空中飞行，逐帧扫描射线（防止高速穿墙），
## 命中墙体/敌人时结算伤害并生成火花，距离或寿命到头自动回收（对象池复用）。
## 对象池：ProjectilePool 预分配 N 发，命中/寿命结束回收到池里而不是 queue_free；
## 回收时断开 hit_enemy/killed 连接，避免复用后旧回调残留导致重复结算。

signal hit_enemy(headshot: bool)
signal killed(headshot: bool)

const MAX_DISTANCE := 150.0
const MAX_LIFETIME := 2.0
const HIT_MASK := 3  # 1 墙体 + 2 敌人
const ImpactFxScript := preload("res://scripts/impact_fx.gd")

var _dir := Vector3.FORWARD
var _speed := 90.0
var _damage := 25
var _gravity := 2.5
var _vy := 0.0
var _age := 0.0
var _traveled := 0.0
var _scene_root: Node
var _pool: ProjectilePool

# 共享网格/材质：每发子弹不再 new 一份（高频分配优化）
static var _shared_mesh: Mesh
static var _shared_mat: Material

static func fire(scene_root: Node, origin: Vector3, dir: Vector3, speed := 90.0, damage := 25, gravity := 2.5) -> Projectile:
	return ProjectilePool.for_scene(scene_root).acquire(origin, dir, speed, damage, gravity)

## 池内一次性初始化（预分配时调用）
func _init_pooled(pool: ProjectilePool) -> void:
	_pool = pool
	_build_visual()
	_set_active(false)
	visible = false

## 从池中取出并发射
func _acquire(origin: Vector3, dir: Vector3, speed: float, damage: int, gravity: float) -> void:
	_dir = dir.normalized()
	_speed = speed
	_damage = damage
	_gravity = gravity
	_vy = 0.0
	_age = 0.0
	_traveled = 0.0
	_scene_root = _pool.get_parent()
	global_position = origin
	# 节点自身朝向弹道方向（圆柱长轴 +Y 对齐弹道，命中判定用 global_position 不受影响）
	rotation = Basis(Quaternion(Vector3.UP, _dir)).get_euler()
	_set_active(true)
	visible = true

## 命中/寿命结束：回收到池里（断开信号防重复回调）
func _release() -> void:
	_deactivate()
	if _pool != null:
		_pool.recycle(self)
	else:
		queue_free()

## 停用（满池复用时由池调用：只停用，不入可用区）
func _deactivate() -> void:
	_set_active(false)
	visible = false
	for conn in get_signal_connection_list("hit_enemy"):
		hit_enemy.disconnect(conn["callable"] as Callable)
	for conn in get_signal_connection_list("killed"):
		killed.disconnect(conn["callable"] as Callable)

func _set_active(on: bool) -> void:
	set_physics_process(on)

func _build_visual() -> void:
	var mesh := MeshInstance3D.new()
	mesh.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	if _shared_mesh == null:
		var cyl := CylinderMesh.new()
		cyl.top_radius = 0.014
		cyl.bottom_radius = 0.014
		cyl.height = 0.5
		cyl.radial_segments = 6
		var mat := StandardMaterial3D.new()
		mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
		mat.albedo_color = Color(1.0, 0.9, 0.6)
		mat.emission_enabled = true
		mat.emission = Color(1.0, 0.75, 0.35) * 2.5
		_shared_mesh = cyl
		_shared_mat = mat
	mesh.mesh = _shared_mesh
	mesh.material_override = _shared_mat
	add_child(mesh)

func _physics_process(delta: float) -> void:
	_age += delta
	if _age >= MAX_LIFETIME or _traveled >= MAX_DISTANCE:
		_release()
		return
	_vy -= _gravity * delta
	var step := _speed * delta
	var from := global_position
	var to := from + _dir * step + Vector3(0, _vy * delta, 0)
	var query := PhysicsRayQueryParameters3D.create(from, to, HIT_MASK)
	var hit := get_world_3d().direct_space_state.intersect_ray(query)
	if hit:
		global_position = hit.position
		var root: Node = _scene_root if _scene_root != null else get_tree().current_scene
		var collider = hit.collider
		# 部位倍率：enemy.gd 按命中 shape 返回（头部 HitboxHead=2.0，躯干=1.0）
		var mult := 1.0
		if collider != null and collider.has_method("get_shape_multiplier"):
			mult = collider.get_shape_multiplier(int(hit.get("shape", 0)))
		var headshot := mult >= 2.0
		ImpactFxScript.spawn(root, hit.position, hit.normal,
			Color(1.0, 0.9, 0.45) if headshot else Color(1.0, 0.75, 0.4))
		if collider != null and collider.has_method("take_damage"):
			var dmg := maxi(1, roundi(_damage * mult))
			if collider.take_damage(dmg):
				killed.emit(headshot)
			hit_enemy.emit(headshot)
		_release()
		return
	global_position = to
	_traveled += step
