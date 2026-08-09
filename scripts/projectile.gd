class_name Projectile
extends Node3D
## 标准弹道飞行：子弹以恒定速度在空中飞行，逐帧扫描射线（防止高速穿墙），
## 命中墙体/敌人时结算伤害并生成火花，距离或寿命到头自动消失。

signal hit_enemy
signal killed

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

static func fire(scene_root: Node, origin: Vector3, dir: Vector3, speed := 90.0, damage := 25, gravity := 2.5) -> Projectile:
	var p := Projectile.new()
	p._dir = dir.normalized()
	p._speed = speed
	p._damage = damage
	p._gravity = gravity
	p._scene_root = scene_root
	scene_root.add_child(p)
	p.global_position = origin
	p._build_visual()
	return p

func _build_visual() -> void:
	var mesh := MeshInstance3D.new()
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
	cyl.material = mat
	mesh.mesh = cyl
	mesh.transform.basis = Basis(Quaternion(Vector3.UP, _dir))
	add_child(mesh)

func _physics_process(delta: float) -> void:
	_age += delta
	if _age >= MAX_LIFETIME or _traveled >= MAX_DISTANCE:
		queue_free()
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
		ImpactFxScript.spawn(root, hit.position, hit.normal)
		var collider = hit.collider
		if collider != null and collider.has_method("take_damage"):
			if collider.take_damage(_damage):
				killed.emit()
			hit_enemy.emit()
		queue_free()
		return
	global_position = to
	_traveled += step
