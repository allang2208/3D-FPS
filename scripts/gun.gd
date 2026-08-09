extends Node3D
## 程序化拼装 AKM 风格枪械 + 开火：射线命中（层 2=敌人）、枪口闪光、曳光、后坐

const MUZZLE_LOCAL := Vector3(0, 0.02, -0.5)
const FIRE_INTERVAL := 0.13
const DAMAGE := 25

var _recoil := 0.0
var _fire_cd := 0.0
var _flash_t := 0.0
var _flash: OmniLight3D

func _ready() -> void:
	_build_gun()
	_flash = OmniLight3D.new()
	_flash.name = "MuzzleFlash"
	_flash.position = MUZZLE_LOCAL
	_flash.omni_range = 3.0
	_flash.light_color = Color(1.0, 0.8, 0.45)
	_flash.light_energy = 0.0
	_flash.visible = false
	add_child(_flash)

func _process(delta: float) -> void:
	_recoil = maxf(0.0, _recoil - delta * 7.0)
	position.z = -0.5 - _recoil * 0.09
	rotation.x = -_recoil * 0.08
	_flash_t = maxf(0.0, _flash_t - delta)
	_flash.visible = _flash_t > 0.0
	_flash.light_energy = 10.0 * (_flash_t / 0.06)

func _physics_process(delta: float) -> void:
	_fire_cd = maxf(0.0, _fire_cd - delta)
	if Input.mouse_mode != Input.MOUSE_MODE_CAPTURED:
		return
	if _fire_cd <= 0.0 and Input.is_mouse_button_pressed(MOUSE_BUTTON_LEFT):
		_shoot()

func _shoot() -> void:
	_fire_cd = FIRE_INTERVAL
	_recoil = 1.0
	_flash_t = 0.06
	var cam := get_viewport().get_camera_3d()
	if cam == null:
		return
	var from := cam.global_position
	var to := from - cam.global_transform.basis.z * 60.0
	var query := PhysicsRayQueryParameters3D.create(from, to, 2)
	var hit := get_world_3d().direct_space_state.intersect_ray(query)
	if hit and hit.collider:
		_spawn_tracer(from, hit.position)
		if hit.collider.has_method("take_damage"):
			hit.collider.take_damage(DAMAGE)
	else:
		_spawn_tracer(from, to)

func _spawn_tracer(from: Vector3, to: Vector3) -> void:
	var scene_root := get_tree().current_scene
	if scene_root == null:
		return
	var mesh := MeshInstance3D.new()
	var box := BoxMesh.new()
	box.size = Vector3(0.015, 0.015, 1.0)
	var mat := StandardMaterial3D.new()
	mat.emission_enabled = true
	mat.emission = Color(1.0, 0.85, 0.4)
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	box.material = mat
	mesh.mesh = box
	mesh.global_position = (from + to) * 0.5
	mesh.look_at(to, Vector3.UP)
	mesh.scale.z = from.distance_to(to)
	scene_root.add_child(mesh)
	get_tree().create_timer(0.06).timeout.connect(func() -> void: mesh.queue_free())

func _box(parent: Node3D, size: Vector3, pos: Vector3, color: Color, rot := Vector3.ZERO) -> void:
	var mesh := MeshInstance3D.new()
	var box := BoxMesh.new()
	box.size = size
	var mat := StandardMaterial3D.new()
	mat.albedo_color = color
	mat.roughness = 0.55
	mat.metallic = 0.35
	box.material = mat
	mesh.mesh = box
	mesh.position = pos
	mesh.rotation = rot
	parent.add_child(mesh)

func _build_gun() -> void:
	var dark := Color(0.13, 0.14, 0.16)
	var mid := Color(0.22, 0.23, 0.27)
	var wood := Color(0.32, 0.22, 0.12)
	_box(self, Vector3(0.06, 0.09, 0.42), Vector3.ZERO, mid)
	_box(self, Vector3(0.04, 0.04, 0.30), Vector3(0, 0.02, -0.35), dark)
	_box(self, Vector3(0.05, 0.10, 0.16), Vector3(0, -0.02, 0.28), wood)
	_box(self, Vector3(0.04, 0.13, 0.05), Vector3(0, -0.11, 0.10), dark, Vector3(0.25, 0, 0))
	_box(self, Vector3(0.045, 0.17, 0.07), Vector3(0, -0.14, -0.02), dark)
	_box(self, Vector3(0.02, 0.05, 0.02), Vector3(0, 0.06, -0.20), dark)
