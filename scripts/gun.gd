extends Node3D
## AKM 风格 hitscan 弹道系统：
## - 射线判定（命中敌人层 2 / 墙体层 1），散布随连射增大（bloom）
## - 每次实弹射击必出曳光（Tracer），命中点出火花（ImpactFx），枪口闪光
## - 弹药 30/90，R 换弹；空仓 / 换弹信号通知 HUD

const MUZZLE_LOCAL := Vector3(0, 0.02, -0.5)
const FIRE_INTERVAL := 0.13
const DAMAGE := 25
const MAG_SIZE := 30
const RELOAD_TIME := 1.5
const BULLET_SPEED := 90.0
const BULLET_GRAVITY := 2.5
const BASE_SPREAD := 0.0025
const BLOOM_PER_SHOT := 0.0012
const MAX_SPREAD := 0.018

const ProjectileScript := preload("res://scripts/projectile.gd")

signal shot(ammo_left: int, reserve_left: int)
signal hit
signal reloading
signal reloaded(ammo_left: int, reserve_left: int)
signal empty

var _recoil := 0.0
var _fire_cd := 0.0
var _flash_t := 0.0
var _reload_t := 0.0
var _spread := 0.0
var _flash_light: OmniLight3D
var _flash_mesh: MeshInstance3D
var ammo := MAG_SIZE
var reserve := 90

func _ready() -> void:
	_build_gun()
	_flash_light = OmniLight3D.new()
	_flash_light.name = "MuzzleFlashLight"
	_flash_light.position = MUZZLE_LOCAL
	_flash_light.omni_range = 3.0
	_flash_light.light_color = Color(1.0, 0.8, 0.45)
	_flash_light.light_energy = 0.0
	_flash_light.visible = false
	add_child(_flash_light)
	_flash_mesh = MeshInstance3D.new()
	_flash_mesh.name = "MuzzleFlashMesh"
	var sphere := SphereMesh.new()
	sphere.radius = 0.06
	sphere.height = 0.12
	var fm := StandardMaterial3D.new()
	fm.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	fm.emission_enabled = true
	fm.emission = Color(1.0, 0.75, 0.35) * 3.0
	fm.albedo_color = Color(1.0, 0.85, 0.5)
	sphere.material = fm
	_flash_mesh.mesh = sphere
	_flash_mesh.position = MUZZLE_LOCAL
	_flash_mesh.visible = false
	add_child(_flash_mesh)
	shot.emit(ammo, reserve)

func _process(delta: float) -> void:
	_recoil = maxf(0.0, _recoil - delta * 7.0)
	position.z = -0.5 - _recoil * 0.09
	rotation.x = -_recoil * 0.08
	_flash_t = maxf(0.0, _flash_t - delta)
	_flash_light.visible = _flash_t > 0.0
	_flash_light.light_energy = 10.0 * (_flash_t / 0.06)
	_flash_mesh.visible = _flash_t > 0.0
	if _flash_mesh.visible:
		_flash_mesh.scale = Vector3.ONE * randf_range(0.8, 1.7)

func _physics_process(delta: float) -> void:
	_fire_cd = maxf(0.0, _fire_cd - delta)
	_spread = maxf(0.0, _spread - delta * 0.12)
	if _reload_t > 0.0:
		_reload_t -= delta
		if _reload_t <= 0.0:
			_finish_reload()
		return
	# 换弹不依赖鼠标捕获（释放鼠标/菜单状态下也能换）
	# 空仓自动换弹：打空弹匣立即开始换弹，不再卡在空枪动画
	if ammo <= 0 and reserve > 0:
		_start_reload()
		return
	if Input.is_physical_key_pressed(KEY_R) and ammo < MAG_SIZE and reserve > 0:
		_start_reload()
		return
	if Input.mouse_mode != Input.MOUSE_MODE_CAPTURED:
		return
	if _fire_cd <= 0.0 and Input.is_mouse_button_pressed(MOUSE_BUTTON_LEFT):
		_shoot()

func _start_reload() -> void:
	_reload_t = RELOAD_TIME
	reloading.emit()

func _shoot() -> void:
	_fire_cd = FIRE_INTERVAL
	if ammo <= 0:
		_recoil = 0.3
		empty.emit()
		return
	ammo -= 1
	_spread = minf(MAX_SPREAD, _spread + BLOOM_PER_SHOT)
	_recoil = 1.0
	_flash_t = 0.06
	shot.emit(ammo, reserve)
	var cam := get_viewport().get_camera_3d()
	if cam == null:
		return
	var dir := _aim_dir(cam)
	var origin := global_transform * MUZZLE_LOCAL
	var scene_root: Node = get_tree().current_scene
	if scene_root == null:
		scene_root = get_tree().root
	var proj = ProjectileScript.fire(scene_root, origin, dir, BULLET_SPEED, DAMAGE, BULLET_GRAVITY)
	proj.hit_enemy.connect(_on_projectile_hit)

func _on_projectile_hit() -> void:
	hit.emit()

func _aim_dir(cam: Camera3D) -> Vector3:
	var base := -cam.global_transform.basis.z
	var right := cam.global_transform.basis.x
	var up := cam.global_transform.basis.y
	var r := BASE_SPREAD + _spread
	return (base + right * randf_range(-r, r) + up * randf_range(-r, r)).normalized()

func _finish_reload() -> void:
	var need := MAG_SIZE - ammo
	var take := mini(need, reserve)
	ammo += take
	reserve -= take
	reloaded.emit(ammo, reserve)

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
