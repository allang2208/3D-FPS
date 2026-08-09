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
# 枪械联动微震：与 gun.gd 同参数字段（JITTER_STIFFNESS/DAMPING），
# 相机侧用同一信号的小比例复制，保证“枪抖=画面微动”同频同相
const GUN_JITTER_STIFFNESS := 7000.0 # 与 gun.gd JITTER_STIFFNESS 一致（同频）
const GUN_JITTER_DAMPING := 48.0     # 与 gun.gd JITTER_DAMPING 一致（同相位）
const CAM_JITTER_POS_SCALE := 0.06   # 相机平移脉冲 = 枪械位置脉冲的 6%
const CAM_JITTER_ROT_SCALE := 0.18   # 相机旋转脉冲 = 枪械旋转脉冲的 18%

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
# 枪械联动微震：镜像弹簧（同刚度/阻尼 + 同脉冲源 → 与枪械严格同频同相）
var _cam_jitter_pos := Vector3.ZERO
var _cam_jitter_pos_vel := Vector3.ZERO
var _cam_jitter_rot := Vector3.ZERO
var _cam_jitter_rot_vel := Vector3.ZERO

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

## 开火时由 gun.gd 触发：同源脉冲按比例注入镜像弹簧
func _on_gun_jitter_impulse(pos_impulse: Vector3, rot_impulse: Vector3) -> void:
	_cam_jitter_pos_vel += pos_impulse * CAM_JITTER_POS_SCALE
	_cam_jitter_rot_vel += rot_impulse * CAM_JITTER_ROT_SCALE

func _process(delta: float) -> void:
	_t += delta
	var cam := get_parent() as Camera3D
	if cam == null:
		return
	if _base_fov <= 0.0:
		_base_fov = cam.fov
	_ads_factor = lerpf(_ads_factor, _ads_target, 1.0 - exp(-ADS_SMOOTH * delta))
	_apply_kick(cam, delta)
	_apply_gun_jitter(cam, delta)
	_apply_fov(cam, delta)
	_apply_trauma(cam, delta)

func _apply_gun_jitter(cam: Camera3D, delta: float) -> void:
	# 与 gun.gd 完全相同的弹簧方程，只按比例缩放幅度 → 严格同频同相
	var prev_pos := _cam_jitter_pos
	var prev_rot := _cam_jitter_rot
	var ap := -_cam_jitter_pos * GUN_JITTER_STIFFNESS - _cam_jitter_pos_vel * GUN_JITTER_DAMPING
	_cam_jitter_pos_vel += ap * delta
	_cam_jitter_pos += _cam_jitter_pos_vel * delta
	var ar := -_cam_jitter_rot * GUN_JITTER_STIFFNESS - _cam_jitter_rot_vel * GUN_JITTER_DAMPING
	_cam_jitter_rot_vel += ar * delta
	_cam_jitter_rot += _cam_jitter_rot_vel * delta
	# 只施加旋转变化量（避免累积漂移），平移交给 _apply_trauma 合并
	var rot_delta := _cam_jitter_rot - prev_rot
	cam.rotation += rot_delta

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
	# 枪械联动偏移（_apply_gun_jitter 已算好，只做位置合并，旋转由增量叠加）
	cam.position = _rest_pos + _cam_jitter_pos + Vector3(ox, oy, 0)
