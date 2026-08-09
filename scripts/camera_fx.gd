extends Node3D
## 相机反馈系统（COD 式手感核心）
## - ViewKick：视角后坐弹簧（impulse → 欠阻尼回摆），连发自然叠加、火率自适应
## - FOV 脉冲：指数平滑回落（幅度小、快起慢落，无线性机械感）
## - Trauma 创伤抖动：Perlin 噪声驱动，trauma² 控制强度，命中反馈有机不毛刺
## 挂载方式：作为 Camera3D 的子节点（get_parent() 即相机）

const SHAKE_DECAY := 3.5        # trauma 指数衰减速率
const SHAKE_MAX_OFFSET := 0.045 # 最大平移（米）
const SHAKE_MAX_ROT := 0.03     # 最大旋转（弧度）
const KICK_STIFFNESS := 170.0   # 视角后坐弹簧刚度
const KICK_DAMPING := 15.0      # 视角后坐弹簧阻尼（欠阻尼 → 回摆）
const FOV_PUNCH_DECAY := 6.5    # FOV 指数回落速率
const FOV_SMOOTH := 10.0        # FOV 平滑速率（变焦/复位共用）
const ADS_FOV := 55.0           # 机瞄目标 FOV
const ADS_SMOOTH := 9.0         # 机瞄进出速率
const KICK_ADS_EXTRA_DAMP := 8.0  # 机瞄时后坐额外回正速率（COD：ADS 回正更快）

var _trauma := 0.0
var _kick_pitch := 0.0
var _kick_yaw := 0.0
var _kick_pitch_vel := 0.0
var _kick_yaw_vel := 0.0
var _fov_offset := 0.0
var _base_fov := 0.0
var _ads_factor := 0.0
var _ads_target := 0.0
var _rest_pos := Vector3.ZERO
var _shake_rot_x := 0.0
var _shake_rot_y := 0.0
var _t := 0.0
var _noise := FastNoiseLite.new()

func _ready() -> void:
	_noise.noise_type = FastNoiseLite.TYPE_SIMPLEX_SMOOTH
	_noise.frequency = 3.5
	var cam := get_parent() as Camera3D
	if cam:
		_rest_pos = cam.position

func add_trauma(amount: float) -> void:
	_trauma = minf(1.0, _trauma + amount)

func kick(pitch: float, yaw: float) -> void:
	_kick_pitch_vel += pitch
	_kick_yaw_vel += yaw

func fov_punch(amount: float) -> void:
	_fov_offset = amount

func set_ads(on: bool) -> void:
	_ads_target = 1.0 if on else 0.0

func _process(delta: float) -> void:
	_t += delta
	var cam := get_parent() as Camera3D
	if cam == null:
		return
	if _base_fov <= 0.0:
		_base_fov = cam.fov
	_ads_factor = lerpf(_ads_factor, _ads_target, 1.0 - exp(-ADS_SMOOTH * delta))
	_apply_kick(cam, delta)
	_apply_fov(cam, delta)
	_apply_trauma(cam, delta)

func _apply_kick(cam: Camera3D, delta: float) -> void:
	var prev_p := _kick_pitch
	var prev_y := _kick_yaw
	# 机瞄时后坐回正更快（能量前置、快速收束）
	var ads_damp := exp(-KICK_ADS_EXTRA_DAMP * _ads_factor * delta)
	_kick_pitch_vel *= ads_damp
	_kick_yaw_vel *= ads_damp
	_kick_pitch_vel += (-_kick_pitch * KICK_STIFFNESS - _kick_pitch_vel * KICK_DAMPING) * delta
	_kick_pitch += _kick_pitch_vel * delta
	_kick_yaw_vel += (-_kick_yaw * KICK_STIFFNESS - _kick_yaw_vel * KICK_DAMPING) * delta
	_kick_yaw += _kick_yaw_vel * delta
	cam.rotation.x += _kick_pitch - prev_p
	cam.rotation.y += _kick_yaw - prev_y

func _apply_fov(cam: Camera3D, delta: float) -> void:
	_fov_offset *= exp(-FOV_PUNCH_DECAY * delta)
	var target := lerpf(_base_fov, ADS_FOV, _ads_factor) + _fov_offset
	cam.fov = lerpf(cam.fov, target, 1.0 - exp(-FOV_SMOOTH * delta))

func _apply_trauma(cam: Camera3D, delta: float) -> void:
	_trauma *= exp(-SHAKE_DECAY * delta)
	var s := _trauma * _trauma
	# 旋转：噪声差值法（只施加变化量，避免随机游走累积）
	var nrx := _noise.get_noise_1d(_t * 9.0 + 17.0) * SHAKE_MAX_ROT * s
	var nry := _noise.get_noise_1d(_t * 7.0 + 55.0) * SHAKE_MAX_ROT * s
	cam.rotation.x += nrx - _shake_rot_x
	cam.rotation.y += nry - _shake_rot_y
	_shake_rot_x = nrx
	_shake_rot_y = nry
	# 平移：绝对位置 = 静止位 + 噪声偏移
	var ox := _noise.get_noise_1d(_t * 11.0) * SHAKE_MAX_OFFSET * s
	var oy := _noise.get_noise_1d(_t * 13.0 + 91.3) * SHAKE_MAX_OFFSET * s
	cam.position = _rest_pos + Vector3(ox, oy, 0)
