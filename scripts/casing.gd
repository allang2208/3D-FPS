class_name Casing
extends MeshInstance3D
## 弹壳：开火时从抛壳口飞出，圆柱长轴对齐初速（姿态自然），
## 带重力/翻滚/落地弹跳/墙体反弹（逐帧扫描射线防穿墙），随后消失。
## 网格与材质全局共享，零每发分配。

const LIFETIME_MIN := 1.2
const LIFETIME_MAX := 1.8
const GRAVITY := 14.0
const WALL_MASK := 1  # 墙体 + 地面
const FLOOR_Y := 0.02

var _vel := Vector3.ZERO
var _rot := Vector3.ZERO
var _age := 0.0
var _lifetime := 1.4
var _floor_bounced := false
var _wall_bounced := false

# 共享网格/材质：每颗弹壳不再 new 一份（高频分配优化）
static var _shared_mesh: Mesh
static var _shared_mat: Material

static func spawn(scene_root: Node, origin: Vector3, right: Vector3) -> void:
	var c := Casing.new()
	var vel := right * randf_range(1.2, 1.8) + Vector3(0, randf_range(1.0, 1.6), randf_range(-0.5, -1.0))
	c._vel = vel
	c._rot = Vector3(randf_range(-25.0, 25.0), randf_range(-25.0, 25.0), randf_range(-25.0, 25.0))
	c._lifetime = randf_range(LIFETIME_MIN, LIFETIME_MAX)
	scene_root.add_child(c)
	c.global_position = origin
	# 圆柱长轴（Y）对齐初速方向：抛壳姿态自然（而不是横着飘）
	if vel.length_squared() > 0.0001:
		c.rotation = Basis(Quaternion(Vector3.UP, vel.normalized())).get_euler()
	c._build()

func _build() -> void:
	if _shared_mesh == null:
		var cyl := CylinderMesh.new()
		cyl.top_radius = 0.008
		cyl.bottom_radius = 0.008
		cyl.height = 0.045
		cyl.radial_segments = 8
		var mat := StandardMaterial3D.new()
		mat.albedo_color = Color(0.72, 0.52, 0.22)
		mat.metallic = 0.9
		mat.roughness = 0.35
		_shared_mesh = cyl
		_shared_mat = mat
	mesh = _shared_mesh
	material_override = _shared_mat

func _physics_process(delta: float) -> void:
	_age += delta
	if _age >= _lifetime:
		queue_free()
		return
	_vel.y -= GRAVITY * delta
	var from := global_position
	var to := from + _vel * delta
	if not _floor_bounced and not _wall_bounced:
		var space := get_world_3d().direct_space_state
		var hit := space.intersect_ray(PhysicsRayQueryParameters3D.create(from, to, WALL_MASK))
		if hit:
			var n: Vector3 = hit.normal
			global_position = hit.position + n * 0.001
			if n.y > 0.5:
				# 地面：贴地反弹，损耗水平速度
				_vel.y = -_vel.y * 0.35
				_vel.x *= 0.6
				_vel.z *= 0.6
				_floor_bounced = true
			else:
				# 墙面：沿法线反弹
				_vel = _vel.bounce(n) * 0.35
				_wall_bounced = true
			_rot *= 0.5
			return
	global_position = to
	rotation_degrees += _rot * delta
	# 兜底落地（射线漏检时）
	if global_position.y < FLOOR_Y and not _floor_bounced:
		_floor_bounced = true
		global_position.y = FLOOR_Y
		_vel.y = -_vel.y * 0.35
		_vel.x *= 0.6
		_vel.z *= 0.6
		_rot *= 0.5
