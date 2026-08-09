extends Node3D
## AKM 强反馈枪械（COD 式三层后坐 + juice）
## - GunKick：枪模多轴弹簧后坐（位置 Z 退/Y 沉 + 旋转 pitch/roll），带回弹过冲
## - ViewKick：相机 pitch 上扬 + yaw 随机，指数回正（真正影响弹道，叠加散布）
## - FOV Punch：开火瞬间视场角 +5°，快速回落
## - Juice：枪口闪光 / 弹壳抛壳 / 命中相机抖动 / AKM 枪声 / 换弹声
## - 弹药 30/90，空仓自动换弹 / R 手动；信号契约（shot/hit/reloading/reloaded/empty）保持不变

const MUZZLE_LOCAL := Vector3(0, 0.02, -0.5)
const EJECT_LOCAL := Vector3(0.045, 0.045, -0.10)
const FIRE_INTERVAL := 0.13
const DAMAGE := 25
const MAG_SIZE := 30
const RELOAD_TIME := 1.5
const BULLET_SPEED := 90.0
const BULLET_GRAVITY := 2.5
const BASE_SPREAD := 0.0025
const BLOOM_PER_SHOT := 0.0012
const MAX_SPREAD := 0.018

const BASE_POS := Vector3(0.28, -0.26, -0.5)

# GunKick 弹簧参数（欠阻尼 → 带回弹过冲）
const KICK_STIFFNESS := 210.0
const KICK_DAMPING := 16.0
# ViewKick 指数回正速率（/s）
const VIEW_KICK_RECOVERY := 5.5
# FOV 脉冲
const FOV_PUNCH := 5.0
const FOV_PUNCH_DECAY := 28.0
# 命中抖动
const HIT_SHAKE_AMP := 0.014
const HIT_SHAKE_TIME := 0.12

const ProjectileScript := preload("res://scripts/projectile.gd")
const CasingScript := preload("res://scripts/casing.gd")
const SHOOT_SOUND := preload("res://assets/sfx/akm_burst.mp3")
const RELOAD_SOUND := preload("res://assets/sfx/reload_sharp.mp3")

signal shot(ammo_left: int, reserve_left: int)
signal hit
signal reloading
signal reloaded(ammo_left: int, reserve_left: int)
signal empty

var _fire_cd := 0.0
var _flash_t := 0.0
var _reload_t := 0.0
var _spread := 0.0
var _flash_light: OmniLight3D
var _flash_mesh: MeshInstance3D
var _shoot_player: AudioStreamPlayer
var _reload_player: AudioStreamPlayer
var ammo := MAG_SIZE
var reserve := 90

# 弹簧状态
var _kick_pos := Vector3.ZERO
var _kick_pos_vel := Vector3.ZERO
var _kick_rot := Vector3.ZERO
var _kick_rot_vel := Vector3.ZERO
# 视角后坐 / FOV / 抖动
var _kick_pitch := 0.0
var _kick_yaw := 0.0
var _fov_kick := 0.0
var _base_fov := 0.0
var _shake_t := 0.0

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
	_shoot_player = AudioStreamPlayer.new()
	_shoot_player.name = "ShootSfx"
	_shoot_player.stream = SHOOT_SOUND
	_shoot_player.volume_db = -2.0
	add_child(_shoot_player)
	_reload_player = AudioStreamPlayer.new()
	_reload_player.name = "ReloadSfx"
	_reload_player.stream = RELOAD_SOUND
	_reload_player.volume_db = -4.0
	add_child(_reload_player)
	shot.emit(ammo, reserve)

func _process(delta: float) -> void:
	_update_spring(delta)
	position = BASE_POS + _kick_pos
	rotation = _kick_rot
	_flash_t = maxf(0.0, _flash_t - delta)
	_flash_light.visible = _flash_t > 0.0
	_flash_light.light_energy = 10.0 * (_flash_t / 0.06)
	_flash_mesh.visible = _flash_t > 0.0
	if _flash_mesh.visible:
		_flash_mesh.scale = Vector3.ONE * randf_range(0.8, 1.7)
	var cam := get_viewport().get_camera_3d()
	if cam != null:
		if _base_fov <= 0.0:
			_base_fov = cam.fov
		_apply_view_kick(cam, delta)
		_apply_fov_punch(cam, delta)
		_apply_hit_shake(cam, delta)

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
	_reload_player.pitch_scale = randf_range(0.95, 1.05)
	_reload_player.play()
	reloading.emit()

func _shoot() -> void:
	_fire_cd = FIRE_INTERVAL
	if ammo <= 0:
		empty.emit()
		return
	ammo -= 1
	_spread = minf(MAX_SPREAD, _spread + BLOOM_PER_SHOT)
	_flash_t = 0.06
	shot.emit(ammo, reserve)
	_apply_gun_kick()
	_shoot_player.pitch_scale = randf_range(0.97, 1.03)
	_shoot_player.play()
	_spawn_casing()
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
	_shake_t = HIT_SHAKE_TIME
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

# ---------- 强反馈 ----------

func _apply_gun_kick() -> void:
	_kick_pos_vel += Vector3(randf_range(-0.10, 0.10), randf_range(0.04, 0.10), randf_range(0.55, 0.85))
	_kick_rot_vel += Vector3(randf_range(0.55, 1.0), 0.0, randf_range(-0.7, 0.7))
	_kick_pitch += randf_range(0.008, 0.017)
	_kick_yaw += randf_range(-0.006, 0.006)
	_fov_kick = FOV_PUNCH

func _update_spring(delta: float) -> void:
	var a_pos := -_kick_pos * KICK_STIFFNESS - _kick_pos_vel * KICK_DAMPING
	_kick_pos_vel += a_pos * delta
	_kick_pos += _kick_pos_vel * delta
	var a_rot := -_kick_rot * KICK_STIFFNESS - _kick_rot_vel * KICK_DAMPING
	_kick_rot_vel += a_rot * delta
	_kick_rot += _kick_rot_vel * delta

func _apply_view_kick(cam: Camera3D, delta: float) -> void:
	var prev_p := _kick_pitch
	var prev_y := _kick_yaw
	var k := exp(-VIEW_KICK_RECOVERY * delta)
	_kick_pitch *= k
	_kick_yaw *= k
	cam.rotation.x += _kick_pitch - prev_p
	cam.rotation.y += _kick_yaw - prev_y

func _apply_fov_punch(cam: Camera3D, delta: float) -> void:
	_fov_kick = maxf(0.0, _fov_kick - delta * FOV_PUNCH_DECAY)
	cam.fov = _base_fov + _fov_kick

func _apply_hit_shake(cam: Camera3D, delta: float) -> void:
	if _shake_t <= 0.0:
		return
	_shake_t -= delta
	var a := HIT_SHAKE_AMP * (_shake_t / HIT_SHAKE_TIME)
	cam.rotation.x += randf_range(-a, a)
	cam.rotation.y += randf_range(-a, a)

func _spawn_casing() -> void:
	var cam := get_viewport().get_camera_3d()
	if cam == null:
		return
	var origin := global_transform * EJECT_LOCAL
	var scene_root: Node = get_tree().current_scene
	if scene_root == null:
		scene_root = get_tree().root
	CasingScript.spawn(scene_root, origin, cam.global_transform.basis.x)

# ---------- 模型 ----------

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
