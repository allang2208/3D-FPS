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
# 枪口高频震颤（CS 式“枪口抖动”：高刚度弹簧冲击 → 短促高频回摆）
const JITTER_STIFFNESS := 7000.0
const JITTER_DAMPING := 48.0
const JITTER_POS_IMPULSE := 0.7
const JITTER_ROT_IMPULSE := 2.2
# ADS 时枪械侧抖动收束系数（相机侧接收已收束的脉冲，两边按同一比例衰减）
const JITTER_ADS_MULT := 0.45
# 枪口翻转（muzzle flip：绕枪口旋转，枪口被顶起、枪身下压）
const FLIP_STIFFNESS := 260.0
const FLIP_DAMPING := 16.0
const FLIP_IMPULSE := 1.5
# 姿态系统（bob / sway / 疾跑下沉）
const BOB_FREQ_BASE := 5.0
const BOB_FREQ_SPEED := 0.85
const SWAY_LAG := 10.0
const SPRINT_DROP := 0.10
const SPRINT_TILT := 0.30
# ADS 机瞄（右键长按）
# 觇孔重合：由后照门(0,0.075,0.09)与前照门(0,0.065,-0.22)反算，
# 使觇孔落在相机中心轴(z≈-0.25)、前照门与觇孔同一水平线
const ADS_POS := Vector3(0, -0.072, -0.342)
const ADS_ROT := Vector3(0.0323, 0, 0)
const ADS_SPREAD_MULT := 0.2
const ADS_SMOOTH := 12.0

const ProjectileScript := preload("res://scripts/projectile.gd")
const CasingScript := preload("res://scripts/casing.gd")
const SHOOT_SOUND := preload("res://assets/sfx/akm_burst.mp3")
const RELOAD_SOUND := preload("res://assets/sfx/reload_sharp.mp3")
const KILL_SOUND := preload("res://assets/sfx/criticalhit.mp3")

signal shot(ammo_left: int, reserve_left: int)
signal hit
signal reloading
signal reloaded(ammo_left: int, reserve_left: int)
signal empty
signal ads_changed(active: bool)
## 开火时发出的枪械震颤脉冲（相机侧镜像弹簧用，保证枪/镜头同频同相零滞后）
signal jitter_impulse(pos_impulse: Vector3, rot_impulse: Vector3)

var _fire_cd := 0.0
var _flash_t := 0.0
var _reload_t := 0.0
var _spread := 0.0
var _flash_light: OmniLight3D
var _flash_mesh: MeshInstance3D
var _shoot_player: AudioStreamPlayer
var _reload_player: AudioStreamPlayer
var _click_player: AudioStreamPlayer
var _smoke: CPUParticles3D
var _shoot_tail: AudioStreamPlayer
var _kill_player: AudioStreamPlayer
var _mag: Node3D
var _mag_base_y := -0.14
var _ads := false
var _ads_factor := 0.0
var _ads_prev := false
var ammo := MAG_SIZE
var reserve := 90

# 弹簧状态
var _kick_pos := Vector3.ZERO
var _kick_pos_vel := Vector3.ZERO
var _kick_rot := Vector3.ZERO
var _kick_rot_vel := Vector3.ZERO
# 高频震颤 / 枪口翻转状态
var _jitter_pos := Vector3.ZERO
var _jitter_pos_vel := Vector3.ZERO
var _jitter_rot := Vector3.ZERO
var _jitter_rot_vel := Vector3.ZERO
var _flip_rot := 0.0
var _flip_vel := 0.0
# 姿态状态
var _bob_t := 0.0
var _bob_pos := Vector3.ZERO
var _bob_rot := Vector3.ZERO
var _sway_pos := Vector3.ZERO
var _sway_rot := Vector3.ZERO
var _sprint := 0.0
var _player: CharacterBody3D

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
	_shoot_tail = AudioStreamPlayer.new()
	_shoot_tail.name = "ShootSfxTail"
	_shoot_tail.stream = SHOOT_SOUND
	_shoot_tail.volume_db = -8.0
	add_child(_shoot_tail)
	_kill_player = AudioStreamPlayer.new()
	_kill_player.name = "KillSfx"
	_kill_player.stream = KILL_SOUND
	_kill_player.volume_db = -2.0
	add_child(_kill_player)
	_click_player = AudioStreamPlayer.new()
	_click_player.name = "DryClick"
	_click_player.stream = _make_click()
	_click_player.volume_db = -6.0
	add_child(_click_player)
	_smoke = CPUParticles3D.new()
	_smoke.name = "MuzzleSmoke"
	_smoke.position = MUZZLE_LOCAL + Vector3(0, -0.01, 0)
	_smoke.one_shot = true
	_smoke.emitting = false
	_smoke.amount = 8
	_smoke.lifetime = 0.45
	_smoke.direction = Vector3(0, 0, -1)
	_smoke.spread = 18.0
	_smoke.gravity = Vector3(0, 0.8, 0)
	_smoke.initial_velocity_min = 0.6
	_smoke.initial_velocity_max = 1.4
	_smoke.scale_amount_min = 0.03
	_smoke.scale_amount_max = 0.07
	_smoke.color = Color(0.75, 0.75, 0.8, 0.5)
	add_child(_smoke)
	_player = get_parent().get_parent() as CharacterBody3D
	# 相机联动：镜像弹簧同参数驱动（枪/镜头同频同相）
	var cam := get_viewport().get_camera_3d()
	if cam:
		var cfx := cam.get_node_or_null("CameraFx")
		if cfx and cfx.has_method("_on_gun_jitter_impulse"):
			jitter_impulse.connect(cfx._on_gun_jitter_impulse)
	shot.emit(ammo, reserve)

func _process(delta: float) -> void:
	_update_spring(delta)
	_update_jitter(delta)
	_update_pose(delta)
	_ads_factor = lerpf(_ads_factor, 1.0 if _ads else 0.0, 1.0 - exp(-ADS_SMOOTH * delta))
	var ads_active := _ads_factor > 0.5
	if ads_active != _ads_prev:
		_ads_prev = ads_active
		ads_changed.emit(ads_active)
	var cam := get_viewport().get_camera_3d()
	if cam:
		var cfx := cam.get_node_or_null("CameraFx")
		if cfx:
			cfx.set_ads(_ads_factor > 0.5)
	var base_pos := BASE_POS.lerp(ADS_POS, _ads_factor)
	var base_rot := Vector3.ZERO.lerp(ADS_ROT, _ads_factor)
	var suppress := 1.0 - _ads_factor
	var reload_pos := Vector3.ZERO
	var reload_rot := Vector3.ZERO
	if _reload_t > 0.0:
		var prog := 1.0 - _reload_t / RELOAD_TIME
		var p := sin(prog * PI)
		reload_pos = Vector3(0, -p * 0.12, p * 0.05)
		reload_rot = Vector3(-p * 0.45, 0, -p * 0.35)
		if _mag:
			_mag.position.y = _mag_base_y - p * 0.18
	# 枪口翻转：绕枪口旋转的位置补偿（枪口保持，枪身下压）
	var flip_correction := Vector3.ZERO
	if absf(_flip_rot) > 0.0005:
		var rb := Basis(Vector3.RIGHT, _flip_rot)
		flip_correction = rb * MUZZLE_LOCAL - MUZZLE_LOCAL
	position = base_pos + _kick_pos + _jitter_pos + _bob_pos * suppress + _sway_pos * suppress + Vector3(0, -SPRINT_DROP * _sprint, 0) * suppress + reload_pos + flip_correction
	rotation = base_rot + _kick_rot + _jitter_rot + _bob_rot * suppress + _sway_rot * suppress + Vector3(SPRINT_TILT * _sprint, 0, 0) * suppress + reload_rot + Vector3(_flip_rot, 0, 0)
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
		_ads = false
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
		_ads = false
		return
	_ads = Input.is_mouse_button_pressed(MOUSE_BUTTON_RIGHT)
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
		_click_player.play()
		empty.emit()
		return
	ammo -= 1
	_spread = minf(MAX_SPREAD, _spread + BLOOM_PER_SHOT)
	_flash_t = 0.06
	shot.emit(ammo, reserve)
	_apply_gun_kick()
	_shoot_player.pitch_scale = randf_range(0.97, 1.03)
	_shoot_player.play()
	_shoot_tail.pitch_scale = randf_range(0.80, 0.86)
	_shoot_tail.play()
	_smoke.restart()
	_spawn_casing()
	var cam := get_viewport().get_camera_3d()
	if cam == null:
		return
	_fire_camera_fx(cam)
	var dir := _aim_dir(cam)
	var origin := global_transform * MUZZLE_LOCAL
	var scene_root: Node = get_tree().current_scene
	if scene_root == null:
		scene_root = get_tree().root
	var proj = ProjectileScript.fire(scene_root, origin, dir, BULLET_SPEED, DAMAGE, BULLET_GRAVITY)
	proj.hit_enemy.connect(_on_projectile_hit)
	proj.killed.connect(_on_proj_kill)

func _on_projectile_hit() -> void:
	var cam := get_viewport().get_camera_3d()
	if cam:
		var cfx := cam.get_node_or_null("CameraFx")
		if cfx:
			cfx.add_trauma(0.22)
	hit.emit()

func _on_proj_kill() -> void:
	var cam := get_viewport().get_camera_3d()
	if cam:
		var cfx := cam.get_node_or_null("CameraFx")
		if cfx:
			cfx.add_trauma(0.45)
	_kill_player.pitch_scale = randf_range(0.95, 1.05)
	_kill_player.play()

func _aim_dir(cam: Camera3D) -> Vector3:
	var base := -cam.global_transform.basis.z
	var right := cam.global_transform.basis.x
	var up := cam.global_transform.basis.y
	var r := (BASE_SPREAD + _spread) * lerpf(1.0, ADS_SPREAD_MULT, _ads_factor)
	return (base + right * randf_range(-r, r) + up * randf_range(-r, r)).normalized()

func _finish_reload() -> void:
	var need := MAG_SIZE - ammo
	var take := mini(need, reserve)
	ammo += take
	reserve -= take
	reloaded.emit(ammo, reserve)

func _make_click() -> AudioStreamWAV:
	var rate := 22050
	var frames := int(rate * 0.05)
	var data := PackedByteArray()
	data.resize(frames * 2)
	for i in frames:
		var env := 0.6 * (1.0 - float(i) / frames)
		var s := (randf() * 2.0 - 1.0) * env
		data.encode_s16(i * 2, int(clampf(s, -1.0, 1.0) * 32767.0))
	var wav := AudioStreamWAV.new()
	wav.format = AudioStreamWAV.FORMAT_16_BITS
	wav.mix_rate = rate
	wav.stereo = false
	wav.data = data
	return wav

func _update_pose(delta: float) -> void:
	var spd := 0.0
	if _player:
		spd = Vector2(_player.velocity.x, _player.velocity.z).length()
	var sprinting := Input.is_physical_key_pressed(KEY_SHIFT) and spd > 1.0 and not _ads
	_bob_t += delta * (BOB_FREQ_BASE + spd * BOB_FREQ_SPEED)
	var target_sprint := 1.0 if sprinting else 0.0
	_sprint = lerpf(_sprint, target_sprint, 1.0 - exp(-8.0 * delta))
	if spd <= 0.5:
		_bob_pos = Vector3(0, sin(_bob_t * 0.5) * 0.003, 0)
		_bob_rot = Vector3.ZERO
	else:
		var amp := 1.35 if _sprint > 0.5 else 0.7
		_bob_pos = Vector3(sin(_bob_t) * 0.011 * amp, absf(cos(_bob_t)) * 0.016 * amp, 0)
		_bob_rot = Vector3(sin(_bob_t * 0.5) * 0.010 * amp, 0, sin(_bob_t) * 0.008 * amp)
	var mv := Input.get_last_mouse_velocity()
	var k := 1.0 - exp(-SWAY_LAG * delta)
	_sway_pos = _sway_pos.lerp(Vector3(mv.x * 0.000006, mv.y * 0.000006, 0), k)
	_sway_rot = _sway_rot.lerp(Vector3(mv.y * 0.00002, mv.x * 0.00003, 0), k)

# ---------- 强反馈 ----------

func _apply_gun_kick() -> void:
	# 后坐随连发累积（越扫越抖）
	var accum := 1.0 + (_spread / MAX_SPREAD) * 0.7
	_kick_pos_vel += Vector3(randf_range(-0.10, 0.10), randf_range(0.04, 0.10), randf_range(0.55, 0.85)) * accum
	_kick_rot_vel += Vector3(randf_range(0.55, 1.0), 0.0, randf_range(-0.7, 0.7)) * accum
	# 枪口高频震颤（弹簧冲击，短促回摆）
	var jitter_mult := lerpf(1.0, JITTER_ADS_MULT, _ads_factor)
	var pos_imp := Vector3(randf_range(-1.0, 1.0), randf_range(-1.0, 1.0), randf_range(-1.0, 1.0)) * JITTER_POS_IMPULSE * jitter_mult
	var rot_imp := Vector3(randf_range(-1.0, 1.0), randf_range(-1.0, 1.0), randf_range(-1.0, 1.0)) * JITTER_ROT_IMPULSE * jitter_mult
	_jitter_pos_vel += pos_imp
	_jitter_rot_vel += rot_imp
	jitter_impulse.emit(pos_imp, rot_imp)
	# 枪口翻转
	_flip_vel += FLIP_IMPULSE

func _update_spring(delta: float) -> void:
	var a_pos := -_kick_pos * KICK_STIFFNESS - _kick_pos_vel * KICK_DAMPING
	_kick_pos_vel += a_pos * delta
	_kick_pos += _kick_pos_vel * delta
	var a_rot := -_kick_rot * KICK_STIFFNESS - _kick_rot_vel * KICK_DAMPING
	_kick_rot_vel += a_rot * delta
	_kick_rot += _kick_rot_vel * delta

func _update_jitter(delta: float) -> void:
	var ap := -_jitter_pos * JITTER_STIFFNESS - _jitter_pos_vel * JITTER_DAMPING
	_jitter_pos_vel += ap * delta
	_jitter_pos += _jitter_pos_vel * delta
	var ar := -_jitter_rot * JITTER_STIFFNESS - _jitter_rot_vel * JITTER_DAMPING
	_jitter_rot_vel += ar * delta
	_jitter_rot += _jitter_rot_vel * delta
	var af := -_flip_rot * FLIP_STIFFNESS - _flip_vel * FLIP_DAMPING
	_flip_vel += af * delta
	_flip_rot += _flip_vel * delta

func _fire_camera_fx(cam: Camera3D) -> void:
	var cfx := cam.get_node_or_null("CameraFx")
	if cfx == null:
		return
	cfx.kick(randf_range(0.008, 0.017), randf_range(-0.006, 0.006))
	cfx.fov_punch(2.5)
	cfx.add_trauma(0.06)  # 每发相机微震

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

func _box(parent: Node3D, size: Vector3, pos: Vector3, color: Color, rot := Vector3.ZERO) -> Node3D:
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
	return mesh

func _cyl(parent: Node3D, radius: float, length: float, pos: Vector3, color: Color) -> Node3D:
	var mesh := MeshInstance3D.new()
	var cyl := CylinderMesh.new()
	cyl.top_radius = radius
	cyl.bottom_radius = radius
	cyl.height = length
	cyl.radial_segments = 10
	var mat := StandardMaterial3D.new()
	mat.albedo_color = color
	mat.roughness = 0.42
	mat.metallic = 0.8
	cyl.material = mat
	mesh.mesh = cyl
	mesh.position = pos
	mesh.rotation = Vector3(PI / 2, 0, 0)  # 圆柱轴向 Y → Z（枪口方向）
	parent.add_child(mesh)
	return mesh

func _build_gun() -> void:
	var dark := Color(0.10, 0.11, 0.13)
	var mid := Color(0.19, 0.20, 0.23)
	var wood := Color(0.34, 0.23, 0.13)
	var poly := Color(0.07, 0.08, 0.09)
	# 机匣 + 防尘盖 + 抛壳口
	_box(self, Vector3(0.06, 0.09, 0.42), Vector3.ZERO, mid)
	_box(self, Vector3(0.05, 0.03, 0.30), Vector3(0, 0.05, -0.02), dark, Vector3(0.05, 0, 0))
	_box(self, Vector3(0.018, 0.025, 0.05), Vector3(0.028, 0.035, 0.02), Color(0.05, 0.05, 0.06))
	# 枪管 + 枪口制退器（枪口在 z≈-0.50）
	_cyl(self, 0.018, 0.34, Vector3(0, 0.02, -0.38), dark)
	_cyl(self, 0.026, 0.07, Vector3(0, 0.02, -0.51), dark)
	# 导气管
	_cyl(self, 0.011, 0.20, Vector3(0, 0.048, -0.27), dark)
	# 护木（上木下黑）
	_box(self, Vector3(0.048, 0.026, 0.20), Vector3(0, 0.005, -0.28), wood)
	_box(self, Vector3(0.05, 0.026, 0.20), Vector3(0, -0.018, -0.28), dark)
	# 枪托 + 抵肩板
	_box(self, Vector3(0.05, 0.10, 0.16), Vector3(0, -0.02, 0.28), wood)
	_box(self, Vector3(0.052, 0.11, 0.02), Vector3(0, -0.02, 0.365), poly)
	# 握把（聚合物）
	_box(self, Vector3(0.04, 0.13, 0.05), Vector3(0, -0.11, 0.10), poly, Vector3(0.25, 0, 0))
	# 弹匣（独立节点，供换弹动画滑出）+ 底座
	_mag = _box(self, Vector3(0.045, 0.17, 0.07), Vector3(0, -0.14, -0.02), dark)
	_box(_mag, Vector3(0.05, 0.012, 0.08), Vector3(0, -0.088, 0), poly)
	# 瞄具：后照门 + 准星座
	_box(self, Vector3(0.028, 0.016, 0.03), Vector3(0, 0.075, 0.09), dark)
	_box(self, Vector3(0.02, 0.045, 0.016), Vector3(0, 0.065, -0.22), dark)
	# 顶部导轨（瞄具/红点安装位）
	_box(self, Vector3(0.032, 0.014, 0.12), Vector3(0, 0.062, 0.03), dark)
