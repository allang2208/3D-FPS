extends Node3D
## 强反馈枪械（COD 式三层后坐 + juice）· 数据驱动（GunData）
## - GunKick：枪模多轴弹簧后坐（位置 Z 退/Y 沉 + 旋转 pitch/roll），带回弹过冲
## - ViewKick：相机 pitch 上扬 + yaw 随机，指数回正（真正影响弹道，叠加散布）
## - FOV Punch：开火瞬间视场角 +5°，快速回落
## - Juice：枪口闪光 / 弹壳抛壳 / 命中相机抖动 / 枪声 / 换弹声
## - 弹药/伤害/射速/后坐力 pattern/扩散惩罚等全部来自 WeaponData（weapon_data/*.tres），
##   空仓自动换弹 / R 手动；信号契约（shot/hit/reloading/reloaded/empty/ammo/reserve）保持不变
## - 移植自 Unity FPS 参考（SakanakoChan/FPSGameBySakanako）：弹道后坐力 pattern、移动/空中扩散惩罚、
##   冲刺开火延迟、贴墙弹道起点修正、部位伤害（爆头 ×2，由 projectile→enemy Hitbox 结算）

## 武器数据（GunData）：缺省 AKM；换枪 = 换 data + model_scene
@export var data: WeaponData = preload("res://weapon_data/akm_dl.tres")

const BASE_POS := Vector3(0.28, -0.15, -0.5)  # 抬高持枪位，给换弹弹匣下滑留出画面空间

# 视模自动校准（从 GLB 网格测量，换枪模自动适配）
const VIEWMODEL_LENGTH := 0.62          # 视模全长目标（米）
const ADS_REAR_CLEAR := 0.13            # ADS 时枪托末端距相机最小距离（米）
const ADS_REAR_DIST_MIN := 0.38         # 照门到相机距离下限
const ADS_REAR_DIST_MAX := 0.75         # 上限（枪不能太远）

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
# 枪口火光：纯粒子方案（CPUParticles3D 一发自毁：主闪光爆点 + 火舌 + 火星 + 点光源）
const FLASH_DURATION := 0.08
const FLASH_LIGHT_PEAK := 5.0
# 姿态系统（bob / sway / 疾跑下沉）
const BOB_FREQ_BASE := 5.0
const BOB_FREQ_SPEED := 0.85
const SWAY_LAG := 10.0
const SPRINT_DROP := 0.10
const SPRINT_TILT := 0.30
# ADS 机瞄（右键长按）：运行时由 _calibrate_viewmodel() 按枪模网格自动计算，
# 保证觇孔/准星落在相机光轴上；换枪模无需手调
var _ads_pos := Vector3(0, -0.072, -0.342)
var _ads_rot := Vector3(0.0323, 0, 0)

const ProjectileScript := preload("res://scripts/projectile.gd")
const CasingScript := preload("res://scripts/casing.gd")

# 枪模资源（运行时从 data.model_scene 取；换枪时替换）
var model_scene: Resource
# 独立弹匣 Mesh（体素枪械用，换弹动画滑出真弹匣）
var mag_scene: Resource
# 枪口方向手动覆盖：0=自动，1=枪口朝+axis，-1=枪口朝-axis（自动判定误判时用）
var muzzle_sign_override := 0.0
var _mag_slide := 0.18

signal shot(ammo_left: int, reserve_left: int)
signal hit
## 爆头命中（供 UI 后续做金色 hitmarker 等）
signal headshot
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
var _pattern_idx := 0
var _last_fire_t := -100.0
var _move_spread := 0.0
var _air_spread := 0.0
var _sprint_lock := 0.0
var _flash_light: OmniLight3D
var _flash_pop: CPUParticles3D
var _flash_flame: CPUParticles3D
var _flash_sparks: CPUParticles3D
var _shoot_player: AudioStreamPlayer
var _reload_player: AudioStreamPlayer
var _click_player: AudioStreamPlayer
var _smoke: CPUParticles3D
var _shoot_tail: AudioStreamPlayer
var _kill_player: AudioStreamPlayer
var _mag: Node3D
var _mag_base_y := -0.14
var _model: Node3D
var _muzzle_local := Vector3(0, 0.02, -0.5)
var _eject_local := Vector3(0.045, 0.045, -0.10)
# 校准结果（调试/测试用）：瞄具锚点在枪节点局部空间的坐标
var _sight_rear := Vector3.ZERO
var _sight_front := Vector3.ZERO
var _rear_dist := 0.0
var _ads := false
var _ads_factor := 0.0
var _ads_prev := false
var ammo := 0
var reserve := 0

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
var _cam: Camera3D

# 物品强化/改造/附魔生效（weapon_formula.gd -> main 调用）：伤害/射速/弹匣/备弹/换弹/散布
var _mod_damage := 0
var _mod_damage_mult := 1.0
var _mod_interval_ms := 0
var _mod_interval_mul := 1.0
var _mod_mag := 0
var _mod_reserve := 0
var _mod_reload_ms := 0
var _mod_spread := 0.0

func apply_item_mods(mods: Dictionary) -> void:
	if data == null:
		return
	_mod_damage = int(mods.get("enhance_flat_damage", 0))
	_mod_damage_mult = 1.0 + float(mods.get("damagePercent", 0.0))
	_mod_interval_ms = int(mods.get("attackIntervalDelta", 0))
	_mod_interval_mul = float(mods.get("attackIntervalMul", 1.0))
	_mod_mag = int(mods.get("magazineDelta", 0))
	_mod_reserve = int(mods.get("reserveDelta", 0))
	_mod_reload_ms = int(mods.get("reloadTimeDelta", 0))
	_mod_spread = float(mods.get("shotSpreadDelta", 0.0))
	reserve = maxi(0, data.reserve + _mod_reserve)
	ammo = mini(ammo, _effective_mag())

func clear_item_mods() -> void:
	apply_item_mods({})

func _effective_mag() -> int:
	if data == null:
		return 1
	return maxi(1, data.mag_size + _mod_mag)

func _ready() -> void:
	if data == null:
		data = load("res://weapon_data/akm_dl.tres")
	if data == null:
		push_error("[gun] 缺少武器数据，使用脚本默认兜底")
		data = WeaponData.new()
	model_scene = data.model_scene
	muzzle_sign_override = data.muzzle_sign_override
	mag_scene = data.mag_scene
	ammo = data.mag_size
	reserve = data.reserve
	_cam = get_parent() as Camera3D
	_build_gun()
	_calibrate_viewmodel()
	_flash_light = OmniLight3D.new()
	_flash_light.name = "MuzzleFlashLight"
	_flash_light.position = _muzzle_local
	_flash_light.omni_range = 2.2
	_flash_light.light_color = Color(1.0, 0.92, 0.5)
	_flash_light.light_energy = 0.0
	_flash_light.visible = false
	add_child(_flash_light)
	# 纯粒子枪口火光：主闪光爆点 + 火舌 + 火星（CPUParticles3D 一发自毁，无贴图）
	_flash_pop = _make_flash_pop()
	add_child(_flash_pop)
	_flash_flame = _make_flash_flame()
	add_child(_flash_flame)
	_flash_sparks = _make_flash_sparks()
	add_child(_flash_sparks)
	_shoot_player = AudioStreamPlayer.new()
	_shoot_player.name = "ShootSfx"
	_shoot_player.stream = data.shoot_sound
	_shoot_player.volume_db = -2.0
	add_child(_shoot_player)
	_reload_player = AudioStreamPlayer.new()
	_reload_player.name = "ReloadSfx"
	_reload_player.stream = data.reload_sound
	_reload_player.volume_db = -4.0
	add_child(_reload_player)
	_shoot_tail = AudioStreamPlayer.new()
	_shoot_tail.name = "ShootSfxTail"
	_shoot_tail.stream = data.shoot_sound
	_shoot_tail.volume_db = -8.0
	add_child(_shoot_tail)
	_kill_player = AudioStreamPlayer.new()
	_kill_player.name = "KillSfx"
	_kill_player.stream = data.kill_sound
	_kill_player.volume_db = -2.0
	add_child(_kill_player)
	_click_player = AudioStreamPlayer.new()
	_click_player.name = "DryClick"
	_click_player.stream = _make_click()
	_click_player.volume_db = -6.0
	add_child(_click_player)
	_smoke = CPUParticles3D.new()
	_smoke.name = "MuzzleSmoke"
	_smoke.position = _muzzle_local + Vector3(0, -0.01, 0)
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
	var cam := _camera()
	if cam:
		var cfx := cam.get_node_or_null("CameraFx")
		if cfx and cfx.has_method("_on_gun_jitter_impulse"):
			jitter_impulse.connect(cfx._on_gun_jitter_impulse)
	shot.emit(ammo, reserve)

func _process(delta: float) -> void:
	_update_spring(delta)
	_update_jitter(delta)
	_update_pose(delta)
	_ads_factor = lerpf(_ads_factor, 1.0 if _ads else 0.0, 1.0 - exp(-data.ads_smooth * delta))
	var ads_active := _ads_factor > 0.5
	if ads_active != _ads_prev:
		_ads_prev = ads_active
		ads_changed.emit(ads_active)
	var cam := _camera()
	if cam:
		var cfx := cam.get_node_or_null("CameraFx")
		if cfx:
			cfx.set_ads(_ads_factor > 0.5)
	var base_pos := BASE_POS.lerp(_ads_pos, _ads_factor)
	var base_rot := Vector3.ZERO.lerp(_ads_rot, _ads_factor)
	var suppress := 1.0 - _ads_factor
	var reload_pos := Vector3.ZERO
	var reload_rot := Vector3.ZERO
	if _reload_t > 0.0:
		var prog := 1.0 - _reload_t / data.reload_time
		# 换弹分段：卸下旧弹匣(0-0.35) → 停顿/取新弹匣(0.35-0.60) → 插入(0.60-1.0)
		var mag_out := 0.0
		if prog < 0.35:
			mag_out = _ease_out(clampf(prog / 0.35, 0.0, 1.0))
		elif prog < 0.60:
			mag_out = 1.0
		else:
			mag_out = 1.0 - _ease_in(clampf((prog - 0.60) / 0.40, 0.0, 1.0))
		# 枪身上抬 + 抬头右倾：弹匣舱位进画面，弹匣下滑时能看清分离
		reload_pos = Vector3(0, mag_out * 0.18, mag_out * 0.03)
		reload_rot = Vector3(-mag_out * 0.08, 0, mag_out * 0.05)
		if _mag:
			_mag.position.y = _mag_base_y - mag_out * _mag_slide
			# 弹匣卸下时后倾、插入时回正（模拟取出/装回角度）
			_mag.rotation.x = mag_out * 0.45
	else:
		# 换弹结束：弹匣复位（防止停在半途）
		if _mag:
			_mag.position.y = _mag_base_y
			_mag.rotation.x = 0.0
	# 枪口翻转：绕枪口旋转的位置补偿（枪口保持，枪身下压）
	var flip_correction := Vector3.ZERO
	if absf(_flip_rot) > 0.0005:
		var rb := Basis(Vector3.RIGHT, _flip_rot)
		flip_correction = rb * _muzzle_local - _muzzle_local
	position = base_pos + _kick_pos + _jitter_pos + _bob_pos * suppress + _sway_pos * suppress + Vector3(0, -SPRINT_DROP * _sprint, 0) * suppress + reload_pos + flip_correction
	rotation = base_rot + _kick_rot + _jitter_rot + _bob_rot * suppress + _sway_rot * suppress + Vector3(SPRINT_TILT * _sprint, 0, 0) * suppress + reload_rot + Vector3(_flip_rot, 0, 0)
	_flash_t = maxf(0.0, _flash_t - delta)
	var flash_on := _flash_t > 0.0
	_flash_light.visible = flash_on
	if flash_on:
		var life := _flash_t / FLASH_DURATION  # 1 → 0
		_flash_light.light_energy = FLASH_LIGHT_PEAK * life * life

func _physics_process(delta: float) -> void:
	_fire_cd = maxf(0.0, _fire_cd - delta)
	_spread = maxf(0.0, _spread - delta * data.spread_decay)
	_sprint_lock = maxf(0.0, _sprint_lock - delta)
	_update_spread_punishments(delta)
	_update_recoil_recovery(delta)
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
	if Input.is_physical_key_pressed(KEY_R) and ammo < data.mag_size and reserve > 0:
		_start_reload()
		return
	if Input.mouse_mode != Input.MOUSE_MODE_CAPTURED:
		_ads = false
		return
	var sprinting := _is_sprinting()
	if sprinting:
		_sprint_lock = data.sprint_to_fire
		_ads = false
	else:
		_ads = Input.is_mouse_button_pressed(MOUSE_BUTTON_RIGHT)
	if _fire_cd <= 0.0 and Input.is_mouse_button_pressed(MOUSE_BUTTON_LEFT):
		_shoot()

func _start_reload() -> void:
	_reload_t = maxf(0.1, data.reload_time + _mod_reload_ms / 1000.0)
	_reload_player.pitch_scale = randf_range(0.95, 1.05)
	_reload_player.play()
	reloading.emit()

func _shoot() -> void:
	if _sprint_lock > 0.0:
		return
	_fire_cd = maxf(0.05, data.fire_interval * _mod_interval_mul + _mod_interval_ms / 1000.0)
	if ammo <= 0:
		_click_player.play()
		empty.emit()
		return
	ammo -= 1
	_spread = minf(data.max_spread, _spread + data.bloom_per_shot)
	_last_fire_t = Time.get_ticks_msec() * 0.001
	var pattern: Vector2 = data.recoil_pattern[_pattern_idx]
	_pattern_idx = mini(_pattern_idx + 1, data.recoil_pattern.size() - 1)
	_flash_t = FLASH_DURATION
	_flash_pop.restart()
	_flash_flame.restart()
	_flash_sparks.restart()
	shot.emit(ammo, reserve)
	_apply_gun_kick()
	_shoot_player.pitch_scale = randf_range(0.97, 1.03)
	_shoot_player.play()
	_shoot_tail.pitch_scale = randf_range(0.80, 0.86)
	_shoot_tail.play()
	_smoke.restart()
	_spawn_casing()
	var cam := _camera()
	if cam == null:
		return
	_fire_camera_fx(cam, pattern)
	var dir := _aim_dir(cam)
	var origin := global_transform * _muzzle_local
	# 贴墙修正（Unity 参考）：2m 内命中时子弹从相机出，避免弹道被墙面吞掉
	var probe := PhysicsRayQueryParameters3D.create(cam.global_position, cam.global_position + dir * 2.0, 3)
	if get_world_3d().direct_space_state.intersect_ray(probe):
		origin = cam.global_position
	var scene_root: Node = get_tree().current_scene
	if scene_root == null:
		scene_root = get_tree().root
	var dmg := int(round(data.damage * _mod_damage_mult)) + _mod_damage
	var proj = ProjectileScript.fire(scene_root, origin, dir, data.bullet_speed, dmg, data.bullet_gravity)
	proj.hit_enemy.connect(_on_projectile_hit)
	proj.killed.connect(_on_proj_kill)

func _on_projectile_hit(is_headshot: bool) -> void:
	var cam := _camera()
	if cam:
		var cfx := cam.get_node_or_null("CameraFx")
		if cfx:
			cfx.add_trauma(0.22 + (0.10 if is_headshot else 0.0))
	if is_headshot:
		headshot.emit()
	hit.emit()

func _on_proj_kill(is_headshot: bool) -> void:
	var cam := _camera()
	if cam:
		var cfx := cam.get_node_or_null("CameraFx")
		if cfx:
			cfx.add_trauma(0.45)
	_kill_player.pitch_scale = randf_range(1.08, 1.16) if is_headshot else randf_range(0.95, 1.05)
	_kill_player.play()

func _aim_dir(cam: Camera3D) -> Vector3:
	var base := -cam.global_transform.basis.z
	var right := cam.global_transform.basis.x
	var up := cam.global_transform.basis.y
	var r := (data.base_spread + _mod_spread + _spread + _move_spread + _air_spread) * lerpf(1.0, data.ads_spread_mult, _ads_factor)
	return (base + right * randf_range(-r, r) + up * randf_range(-r, r)).normalized()

## 缓存相机引用（枪挂在 Camera3D 下，避免每帧 get_viewport 查找）
func _camera() -> Camera3D:
	if _cam == null:
		_cam = get_parent() as Camera3D
	return _cam

func _finish_reload() -> void:
	var need := _effective_mag() - ammo
	var take := mini(need, reserve)
	ammo += take
	reserve -= take
	_pattern_idx = 0
	reloaded.emit(ammo, reserve)

# ---------- 弹道后坐力 pattern / 扩散惩罚 / 冲刺开火 ----------

func _is_sprinting() -> bool:
	if _player == null:
		return false
	var spd := Vector2(_player.velocity.x, _player.velocity.z).length()
	return Input.is_physical_key_pressed(KEY_SHIFT) and spd > 1.0

func _update_spread_punishments(delta: float) -> void:
	var spd := 0.0
	if _player:
		spd = Vector2(_player.velocity.x, _player.velocity.z).length()
	var target_move := clampf(spd * data.move_spread_ratio, 0.0, data.max_move_spread)
	_move_spread = lerpf(_move_spread, target_move, 1.0 - exp(-6.0 * delta))
	var airborne := _player != null and not _player.is_on_floor()
	var target_air := data.air_spread_punish if (airborne and not _ads) else 0.0
	_air_spread = lerpf(_air_spread, target_air, 1.0 - exp(-data.air_spread_transition * delta))

func _update_recoil_recovery(_delta: float) -> void:
	var now := Time.get_ticks_msec() * 0.001
	var idle := now - _last_fire_t
	if idle > data.recoil_recovery_delay:
		var shots := int((idle - data.recoil_recovery_delay) / data.recoil_recovery_interval)
		if shots > 0:
			_pattern_idx = maxi(0, _pattern_idx - shots)

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

func _ease_in(t: float) -> float:
	return t * t

func _ease_out(t: float) -> float:
	return 1.0 - (1.0 - t) * (1.0 - t)

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
	var accum := 1.0 + (_spread / data.max_spread) * 0.7
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

func _fire_camera_fx(cam: Camera3D, pattern: Vector2) -> void:
	var cfx := cam.get_node_or_null("CameraFx")
	if cfx == null:
		return
	cfx.kick(pattern.x + randf_range(-0.0012, 0.0012), pattern.y + randf_range(-0.0008, 0.0008))
	cfx.fov_punch(2.5)
	cfx.add_trauma(0.06)  # 每发相机微震

func _spawn_casing() -> void:
	var cam := _camera()
	if cam == null:
		return
	var origin := global_transform * _eject_local
	var scene_root: Node = get_tree().current_scene
	if scene_root == null:
		scene_root = get_tree().root
	CasingScript.spawn(scene_root, origin, cam.global_transform.basis.x)

# ---------- 模型 ----------

## 粒子软边光点（ADD 叠加）：程序化径向渐变贴图去硬边/像素颗粒感，白色由 color_ramp 上色
func _make_particle_mesh(alpha := 1.0) -> Mesh:
	var q := QuadMesh.new()
	q.size = Vector2.ONE
	var m := StandardMaterial3D.new()
	m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	m.blend_mode = BaseMaterial3D.BLEND_MODE_ADD
	m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	m.albedo_texture = _make_soft_dot_texture()
	m.albedo_color = Color(1.0, 1.0, 1.0, alpha)
	m.disable_receive_shadows = true
	q.material = m
	return q

## 软边圆点贴图：中心亮 → 边缘平滑衰减到透明（消除方块硬边）
func _make_soft_dot_texture() -> ImageTexture:
	var size := 64
	var img := Image.create(size, size, false, Image.FORMAT_RGBA8)
	var center := Vector2(size * 0.5, size * 0.5)
	for y in size:
		for x in size:
			var d := Vector2(x + 0.5, y + 0.5).distance_to(center) / (size * 0.5)
			var a := clampf(1.0 - d, 0.0, 1.0)
			a = a * a * (3.0 - 2.0 * a)  # smoothstep 软边
			img.set_pixel(x, y, Color(1, 1, 1, a))
	return ImageTexture.create_from_image(img)

func _make_gradient(offsets: PackedFloat32Array, colors: PackedColorArray) -> Gradient:
	var g := Gradient.new()
	g.offsets = offsets
	g.colors = colors
	return g

func _make_curve(points: Array) -> Curve:
	var c := Curve.new()
	for p in points:
		c.add_point(p)
	return c

## 主闪光爆点：枪口处一次性爆开的亮团（方向略散、速度慢、极短命）
func _make_flash_pop() -> CPUParticles3D:
	var p := CPUParticles3D.new()
	p.name = "MuzzleFlashPop"
	p.mesh = _make_particle_mesh(0.95)
	p.one_shot = true
	p.emitting = false
	p.amount = 8
	p.lifetime = 0.06
	p.explosiveness = 1.0
	p.randomness = 0.8
	p.direction = Vector3(0, 0, -1)
	p.spread = 40.0
	p.gravity = Vector3.ZERO
	p.initial_velocity_min = 0.6
	p.initial_velocity_max = 2.6
	p.damping_min = 6.0
	p.damping_max = 10.0
	p.scale_amount_min = 0.05
	p.scale_amount_max = 0.11
	p.scale_amount_curve = _make_curve([Vector2(0, 0.45), Vector2(0.35, 1.0), Vector2(1, 0.12)])
	p.color_ramp = _make_gradient(
		PackedFloat32Array([0.0, 0.35, 0.7, 1.0]),
		PackedColorArray([Color(1, 0.98, 0.75), Color(1, 0.9, 0.45), Color(1, 0.75, 0.2), Color(1, 0.6, 0.1, 0.0)]))
	p.position = _muzzle_local
	return p

## 火舌：沿枪管方向喷出的窄锥火焰（粒子被阻尼拉住、逐渐缩小，模拟燃烧减速）
func _make_flash_flame() -> CPUParticles3D:
	var p := CPUParticles3D.new()
	p.name = "MuzzleFlashFlame"
	p.mesh = _make_particle_mesh(0.9)
	p.one_shot = true
	p.emitting = false
	p.amount = 16
	p.lifetime = 0.11
	p.explosiveness = 0.8
	p.randomness = 0.6
	p.direction = Vector3(0, 0, -1)
	p.spread = 14.0
	p.gravity = Vector3(0, -0.5, 0)
	p.initial_velocity_min = 5.0
	p.initial_velocity_max = 11.0
	p.damping_min = 4.0
	p.damping_max = 8.0
	p.scale_amount_min = 0.035
	p.scale_amount_max = 0.075
	p.scale_amount_curve = _make_curve([Vector2(0, 1.0), Vector2(0.55, 0.55), Vector2(1, 0.12)])
	p.angular_velocity_min = -60.0
	p.angular_velocity_max = 60.0
	p.color_ramp = _make_gradient(
		PackedFloat32Array([0.0, 0.2, 0.45, 0.75, 1.0]),
		PackedColorArray([
			Color(1, 0.96, 0.7), Color(1, 0.88, 0.42), Color(1, 0.78, 0.28),
			Color(0.95, 0.65, 0.15), Color(0.85, 0.55, 0.1, 0.0)]))
	p.position = _muzzle_local + Vector3(0, 0, -0.03)
	return p

## 火星：向四周喷溅的细小亮点（重力下落 + 翻滚），寿命较长
func _make_flash_sparks() -> CPUParticles3D:
	var p := CPUParticles3D.new()
	p.name = "MuzzleFlashSparks"
	p.mesh = _make_particle_mesh(0.95)
	p.one_shot = true
	p.emitting = false
	p.amount = 6
	p.lifetime = 0.22
	p.explosiveness = 1.0
	p.randomness = 0.9
	p.direction = Vector3(0, 0, -1)
	p.spread = 55.0
	p.gravity = Vector3(0, -9, 0)
	p.initial_velocity_min = 7.0
	p.initial_velocity_max = 16.0
	p.damping_min = 1.0
	p.damping_max = 2.5
	p.scale_amount_min = 0.012
	p.scale_amount_max = 0.03
	p.angular_velocity_min = 180.0
	p.angular_velocity_max = 420.0
	p.color_ramp = _make_gradient(
		PackedFloat32Array([0.0, 0.5, 1.0]),
		PackedColorArray([Color(1, 0.95, 0.6), Color(1, 0.8, 0.35), Color(1, 0.65, 0.2, 0.0)]))
	p.position = _muzzle_local + Vector3(0, 0, -0.04)
	return p

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
	# AI 生成 AKM（TRELLIS.2）：朝向/缩放由 _calibrate_viewmodel() 按网格测量
	var akm: Node3D
	if model_scene is PackedScene:
		akm = (model_scene as PackedScene).instantiate()
	elif model_scene is Mesh:
		# 体素模型：OBJ/PLY 直接挂 MeshInstance3D，顶点色 + 无光照（像素风）
		# 必须包一层 Node3D：旋转/缩放由父节点承担，MeshInstance3D 保持单位变换，
		# 否则 _mesh_vertices 的 mi.transform 与校准 to_gun 会双重旋转导致枪口反。
		var holder := Node3D.new()
		holder.name = "AkmModel"
		var mi := MeshInstance3D.new()
		mi.mesh = model_scene as Mesh
		# Godot OBJ 导入会归一化到原点（坐标 0..1.005），这里按 AABB 中心反移，
		# 把网格真正居中到节点原点，校准/弹匣/枪口定位才与导出坐标系一致
		mi.position = -(mi.mesh.get_aabb().get_center())
		var arrays := (mi.mesh as ArrayMesh).surface_get_arrays(0)
		if arrays.size() > 0 and arrays[Mesh.ARRAY_COLOR] != null:
			var mat := StandardMaterial3D.new()
			mat.vertex_color_use_as_albedo = true
			mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
			mi.material_override = mat
		holder.add_child(mi)
		akm = holder
	else:
		push_error("[gun] model_scene 类型不支持：", model_scene.get_class())
		return
	akm.name = "AkmModel"
	add_child(akm)
	_model = akm
	# 弹匣：体素枪械用独立弹匣 Mesh（真弹匣滑出）；GLB 仍用程序化占位盒
	if model_scene is Mesh and mag_scene is Mesh:
		var mag_holder := Node3D.new()
		mag_holder.name = "Magazine"
		var mag_mi := MeshInstance3D.new()
		mag_mi.mesh = mag_scene as Mesh
		mag_mi.position = -(mag_mi.mesh.get_aabb().get_center())
		var marr := (mag_mi.mesh as ArrayMesh).surface_get_arrays(0)
		if marr.size() > 0 and marr[Mesh.ARRAY_COLOR] != null:
			var mmat := StandardMaterial3D.new()
			mmat.vertex_color_use_as_albedo = true
			mmat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
			mag_mi.material_override = mmat
		mag_holder.add_child(mag_mi)
		_model.add_child(mag_holder)
		_mag = mag_holder
	else:
		_mag = _box(self, Vector3(0.05, 0.11, 0.06), Vector3(0, -0.14, -0.02), Color(0.10, 0.11, 0.13))

# ---------- 视模自动校准 ----------

func _calibrate_viewmodel() -> void:
	if _model == null:
		return
	var verts := _mesh_vertices(_model)
	if verts.is_empty():
		push_warning("[gun] 无法读取枪模网格，ADS 使用默认位姿")
		return
	var axis := _dominant_axis(verts)
	if axis == 1:
		push_warning("[gun] 枪模主轴为 Y（立式），暂不支持自动校准")
		return
	var muzzle_sign := _muzzle_sign(verts, axis)
	if muzzle_sign_override != 0.0:
		muzzle_sign = signf(muzzle_sign_override)
		print("[gun] muzzle direction override=", muzzle_sign)
	var extent := _axis_extent(verts, axis)
	if extent <= 0.001:
		return
	# 旋转：让枪口指向 -Z（相机前方）
	var rot_deg := 90.0 if muzzle_sign > 0.0 else -90.0
	if axis == 2:
		rot_deg = 0.0 if muzzle_sign > 0.0 else 180.0
	_model.rotation_degrees.y = rot_deg
	var scale := clampf(VIEWMODEL_LENGTH / extent, 0.4, 1.0)
	_model.scale = Vector3.ONE * scale
	var b := Basis(Vector3.UP, deg_to_rad(rot_deg))
	var to_gun := func(p: Vector3) -> Vector3: return (b * p) * scale
	# 瞄具锚点（raw 网格坐标，t 从枪托端 0 → 枪口端 1）
	var rear_raw := _find_rear_sight(verts, axis, muzzle_sign)
	var front_raw := _find_front_sight(verts, axis, muzzle_sign, rear_raw.y)
	var muzzle_raw := _find_tip(verts, axis, muzzle_sign, true)
	var stock_raw := _find_tip(verts, axis, muzzle_sign, false)
	var rear: Vector3 = to_gun.call(rear_raw)
	var front: Vector3 = to_gun.call(front_raw)
	var muzzle_local_tmp: Vector3 = to_gun.call(muzzle_raw)
	if front_raw == Vector3.ZERO:
		# 找不到前准星（粗模/无准星）：用枪口位置、照门高度构造水平瞄线
		front = Vector3(rear.x, rear.y, (muzzle_local_tmp.z + rear.z) * 0.5)
		push_warning("[gun] 未检出前准星，使用水平瞄线兜底")
	# 前准星高度合理性校验：AI 网格（尤其低模）常在前端产生噪声尖刺被误判为
	# 准星，导致机瞄大幅抬头、枪口高于瞄准线（视觉上像"方向反了"）。
	# 准星高度低于照门 65% 时按水平瞄线兜底（准星取照门高度），姿态恢复正常。
	if rear.y > 0.001 and front.y < rear.y * 0.65:
		push_warning("[gun] 前准星锚点异常（y=", front.y, " < 照门×0.65=", rear.y * 0.65, "），改用水平瞄线")
		front = Vector3(front.x, rear.y, front.z)
	_sight_rear = rear
	_sight_front = front
	_muzzle_local = muzzle_local_tmp
	_eject_local = Vector3(0.035 * scale, 0.032 * scale, _muzzle_local.z + 0.30 * scale)
	if _mag:
		if _mag.get_parent() == _model:
			# 体素独立弹匣：OBJ 与枪体同坐标系，网格自带正确位置，节点放原点即可
			_mag.position = Vector3.ZERO
			_mag_base_y = 0.0
			_mag_slide = 0.30 / scale
		else:
			var mag_center := _find_mag_center(verts, axis, muzzle_sign)
			if mag_center != Vector3.ZERO:
				_mag.position = to_gun.call(mag_center) + Vector3(0, 0.022, 0)
				_mag.scale = Vector3.ONE * scale
				_mag_base_y = _mag.position.y
	# ADS 求解：旋转让照门→准星连线指向相机光轴(-Z)，再平移让照门落到光轴上
	var d: Vector3 = front - rear
	if d.length_squared() < 0.0001:
		push_warning("[gun] 瞄具锚点异常，跳过 ADS 校准")
		return
	var q := Quaternion(Vector3(0, 0, -1), d.normalized())
	var rot_basis := Basis(q.inverse())
	_ads_rot = rot_basis.get_euler()
	var stock_gun: Vector3 = to_gun.call(stock_raw)
	var stock_clear_z: float = (rot_basis * (stock_gun - rear)).z
	_rear_dist = clampf(ADS_REAR_CLEAR + stock_clear_z, ADS_REAR_DIST_MIN, ADS_REAR_DIST_MAX)
	_ads_pos = Vector3(0, 0, -_rear_dist) - rot_basis * rear
	print("[gun] ADS calibrated: pos=", _ads_pos, " rot=", _ads_rot, " rear_dist=", _rear_dist)
	print("[gun] sight rear=", rear, " front=", front, " muzzle=", _muzzle_local, " scale=", scale)

func _mesh_vertices(model: Node3D) -> PackedVector3Array:
	var out := PackedVector3Array()
	if model is MeshInstance3D:
		_append_mesh_verts(model as MeshInstance3D, out)
	for c in model.find_children("*", "MeshInstance3D", true, false):
		_append_mesh_verts(c as MeshInstance3D, out)
	return out

func _append_mesh_verts(mi: MeshInstance3D, out: PackedVector3Array) -> void:
	# 独立弹匣是模型子节点，但测量枪体几何时要排除（弹匣会带偏瞄具/枪口定位）
	var anc := mi.get_parent()
	while anc:
		if anc.name == "Magazine":
			return
		anc = anc.get_parent()
	var mesh := mi.mesh as ArrayMesh
	if mesh == null:
		return
	for s in range(mesh.get_surface_count()):
		var arrays := mesh.surface_get_arrays(s)
		if arrays.is_empty():
			continue
		var v: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
		for p in v:
			out.append(mi.transform * p)

func _dominant_axis(verts: PackedVector3Array) -> int:
	var mn := Vector3(INF, INF, INF)
	var mx := Vector3(-INF, -INF, -INF)
	for v in verts:
		mn = mn.min(v)
		mx = mx.max(v)
	var e := mx - mn
	if e.y > e.x and e.y > e.z:
		return 1
	if e.z > e.x and e.z > e.y:
		return 2
	return 0

func _axis_extent(verts: PackedVector3Array, axis: int) -> float:
	var mn := INF
	var mx := -INF
	for v in verts:
		mn = minf(mn, v[axis])
		mx = maxf(mx, v[axis])
	return mx - mn

func _muzzle_sign(verts: PackedVector3Array, axis: int) -> float:
	# 枪口方向判定：默认 +X（与参考图/TRELLIS 一致，本管线生成的枪模枪口均朝 +X）。
	# 仅当 -X 端出现“明确的前准星立柱”（窄顶带 + 高度在照门 55%~90%）而 +X 端没有时，
	# 才判定枪口朝 -X（镜像枪模）。误判可手动用 muzzle_sign_override 覆盖。
	var n_bins := 120
	var tops := _bin_tops(verts, axis, 1.0, n_bins)
	# 后照门：中段（25%..75%）最高点
	var rear_top := -INF
	for i in range(n_bins):
		var t := (i + 0.5) / n_bins
		if t >= 0.25 and t <= 0.75:
			rear_top = maxf(rear_top, tops[i])
	if rear_top > -INF:
		# 两端各找前准星候选（从端部往回扫，首个满足宽度+高度范围的小凸起）
		var cand_plus := _front_candidate(verts, axis, 0.80, 0.97, rear_top)
		var cand_minus := _front_candidate(verts, axis, 0.03, 0.20, rear_top)
		var ok_plus := cand_plus != Vector3.ZERO
		var ok_minus := cand_minus != Vector3.ZERO
		if ok_minus and not ok_plus:
			return -1.0
	return 1.0

func _front_candidate(verts: PackedVector3Array, axis: int, t_lo: float, t_hi: float, rear_top: float) -> Vector3:
	# 在 [t_lo, t_hi]（t 以 +axis 为枪口端）从端部往回扫：
	# 首个高于局部基线、顶带宽 < 3.5cm、高度在照门 55%~97% 的凸起 = 前准星
	var n_bins := 120
	var tops := _bin_tops(verts, axis, 1.0, n_bins)
	var region: Array[float] = []
	for i in range(n_bins):
		var t := (i + 0.5) / n_bins
		if t >= t_lo and t <= t_hi:
			region.append(tops[i])
	if region.is_empty():
		return Vector3.ZERO
	region.sort()
	var base := region[region.size() / 2]
	var lo := clampi(int(t_lo * n_bins), 0, n_bins - 1)
	var hi := clampi(int(t_hi * n_bins), 0, n_bins - 1)
	for i in range(hi, lo - 1, -1):
		var t := (i + 0.5) / n_bins
		if t < t_lo or t > t_hi:
			continue
		if tops[i] <= base + 0.0025:
			continue
		if tops[i] < rear_top * 0.55 or tops[i] > rear_top * 0.90:
			continue
		var w := _top_band_width(verts, axis, 1.0, i, n_bins, 0.002)
		if w > 0.02:
			continue
		var c := _top_band_centroid(verts, axis, 1.0, i, n_bins, 0.002)
		if c != Vector3.ZERO:
			return c
	return Vector3.ZERO

func _t_of(v: Vector3, axis: int, muzzle_sign: float, mn: float, extent: float) -> float:
	var c := v[axis]
	if muzzle_sign > 0.0:
		return clampf((c - mn) / extent, 0.0, 1.0)
	return clampf((mn + extent - c) / extent, 0.0, 1.0)

func _bin_tops(verts: PackedVector3Array, axis: int, muzzle_sign: float, n_bins: int) -> Array[float]:
	var mn := INF
	var mx := -INF
	for v in verts:
		mn = minf(mn, v[axis])
		mx = maxf(mx, v[axis])
	var extent := mx - mn
	var tops: Array[float] = []
	tops.resize(n_bins)
	tops.fill(-INF)
	for v in verts:
		var t := _t_of(v, axis, muzzle_sign, mn, extent)
		var i := clampi(int(t * n_bins), 0, n_bins - 1)
		tops[i] = maxf(tops[i], v.y)
	return tops

func _top_band(verts: PackedVector3Array, axis: int, muzzle_sign: float, bin_i: int, n_bins: int, band: float) -> Array[Vector3]:
	var mn := INF
	var mx := -INF
	for v in verts:
		mn = minf(mn, v[axis])
		mx = maxf(mx, v[axis])
	var extent := mx - mn
	var t0 := float(bin_i) / n_bins
	var t1 := float(bin_i + 1) / n_bins
	var top := 0.0
	for v in verts:
		var t := _t_of(v, axis, muzzle_sign, mn, extent)
		if t >= t0 and t < t1:
			top = maxf(top, v.y)
	var pts: Array[Vector3] = []
	for v in verts:
		var t := _t_of(v, axis, muzzle_sign, mn, extent)
		if t >= t0 and t < t1 and v.y > top - band:
			pts.append(v)
	return pts

func _top_band_centroid(verts: PackedVector3Array, axis: int, muzzle_sign: float, bin_i: int, n_bins: int, band: float) -> Vector3:
	var pts := _top_band(verts, axis, muzzle_sign, bin_i, n_bins, band)
	if pts.is_empty():
		return Vector3.ZERO
	var sum := Vector3.ZERO
	for p in pts:
		sum += p
	return sum / pts.size()

func _top_band_width(verts: PackedVector3Array, axis: int, muzzle_sign: float, bin_i: int, n_bins: int, band: float) -> float:
	var pts := _top_band(verts, axis, muzzle_sign, bin_i, n_bins, band)
	if pts.size() < 2:
		return 0.0
	var zmin := INF
	var zmax := -INF
	for p in pts:
		zmin = minf(zmin, p.z)
		zmax = maxf(zmax, p.z)
	return zmax - zmin

func _find_rear_sight(verts: PackedVector3Array, axis: int, muzzle_sign: float) -> Vector3:
	var n_bins := 120
	var tops := _bin_tops(verts, axis, muzzle_sign, n_bins)
	var best := -INF
	var best_i := -1
	for i in range(n_bins):
		var t := (i + 0.5) / n_bins
		if t < 0.30 or t > 0.80:
			continue
		if tops[i] > best:
			best = tops[i]
			best_i = i
	if best_i < 0:
		return Vector3.ZERO
	return _top_band_centroid(verts, axis, muzzle_sign, best_i, n_bins, 0.004)

func _find_front_sight(verts: PackedVector3Array, axis: int, muzzle_sign: float, rear_top: float) -> Vector3:
	# 前准星在枪口端一侧；t 以 +axis 为枪口端计算
	if muzzle_sign > 0.0:
		return _front_candidate(verts, axis, 0.78, 0.97, rear_top)
	return _front_candidate(verts, axis, 0.03, 0.22, rear_top)

func _find_tip(verts: PackedVector3Array, axis: int, muzzle_sign: float, is_muzzle: bool) -> Vector3:
	var mn := INF
	var mx := -INF
	for v in verts:
		mn = minf(mn, v[axis])
		mx = maxf(mx, v[axis])
	var extent := mx - mn
	var sum := Vector3.ZERO
	var cnt := 0
	for v in verts:
		var t := _t_of(v, axis, muzzle_sign, mn, extent)
		if (is_muzzle and t > 0.96) or (not is_muzzle and t < 0.04):
			sum += v
			cnt += 1
	if cnt == 0:
		return Vector3.ZERO
	return sum / cnt

func _find_mag_center(verts: PackedVector3Array, axis: int, muzzle_sign: float) -> Vector3:
	var mn := INF
	var mx := -INF
	for v in verts:
		mn = minf(mn, v[axis])
		mx = maxf(mx, v[axis])
	var extent := mx - mn
	var mn_y := INF
	for v in verts:
		var t := _t_of(v, axis, muzzle_sign, mn, extent)
		if t >= 0.42 and t <= 0.62:
			mn_y = minf(mn_y, v.y)
	if mn_y > 900.0:
		return Vector3.ZERO
	var sum := Vector3.ZERO
	var cnt := 0
	for v in verts:
		var t := _t_of(v, axis, muzzle_sign, mn, extent)
		if t >= 0.42 and t <= 0.62 and v.y < mn_y + 0.015:
			sum += v
			cnt += 1
	if cnt == 0:
		return Vector3.ZERO
	return sum / cnt
