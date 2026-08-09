class_name Casing
extends MeshInstance3D
## 弹壳：开火时从抛壳口飞出，带重力/旋转/落地弹跳，随后消失

const LIFETIME := 1.4

var _vel := Vector3.ZERO
var _rot := Vector3.ZERO
var _age := 0.0
var _bounced := false

static func spawn(scene_root: Node, origin: Vector3, right: Vector3) -> void:
	var c := Casing.new()
	c._vel = right * randf_range(1.2, 1.8) + Vector3(0, randf_range(1.0, 1.6), randf_range(-0.5, -1.0))
	c._rot = Vector3(randf_range(-25.0, 25.0), randf_range(-25.0, 25.0), randf_range(-25.0, 25.0))
	scene_root.add_child(c)
	c.global_position = origin
	c._build()

func _build() -> void:
	var box := BoxMesh.new()
	box.size = Vector3(0.018, 0.012, 0.045)
	var mat := StandardMaterial3D.new()
	mat.albedo_color = Color(0.72, 0.52, 0.22)
	mat.metallic = 0.9
	mat.roughness = 0.35
	box.material = mat
	mesh = box

func _physics_process(delta: float) -> void:
	_age += delta
	if _age >= LIFETIME:
		queue_free()
		return
	_vel.y -= 14.0 * delta
	global_position += _vel * delta
	rotation_degrees += _rot * delta
	if global_position.y < 0.02 and not _bounced:
		_bounced = true
		global_position.y = 0.02
		_vel.y = -_vel.y * 0.35
		_vel.x *= 0.6
		_vel.z *= 0.6
		_rot *= 0.5
