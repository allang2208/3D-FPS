class_name WeaponData
extends Resource
## 武器数据（GunData）：Unity FPS 参考（SakanakoChan/FPSGameBySakanako）移植的多武器架构。
## 每把武器一份 .tres（weapon_data/*.tres），gun.gd 只读 data，不再硬编码武器常量。
## 脚本内默认值 = AKM 基准（与 weapon_data/akm.tres 一致），data 缺失时兜底可用。

@export var weapon_name := "AK-74"
@export var model_scene: PackedScene

@export_group("开火")
@export var fire_interval := 0.13
@export var damage := 25
@export var mag_size := 30
@export var reserve := 90
@export var reload_time := 1.5

@export_group("弹道")
@export var bullet_speed := 90.0
@export var bullet_gravity := 2.5
@export var base_spread := 0.0025
@export var bloom_per_shot := 0.0012
@export var max_spread := 0.018
@export var spread_decay := 0.12
@export var ads_spread_mult := 0.2
@export var ads_smooth := 12.0

@export_group("弹道后坐力 pattern")
@export var recoil_pattern := PackedVector2Array([
	Vector2(0.009, 0.0),
	Vector2(0.012, -0.002),
	Vector2(0.015, 0.0025),
	Vector2(0.018, -0.0015),
	Vector2(0.020, 0.003),
	Vector2(0.022, -0.002),
	Vector2(0.024, 0.002),
	Vector2(0.026, -0.001),
	Vector2(0.028, 0.0005),
])
@export var recoil_recovery_delay := 0.30
@export var recoil_recovery_interval := 0.05

@export_group("扩散惩罚")
@export var move_spread_ratio := 0.6
@export var max_move_spread := 0.012
@export var air_spread_punish := 0.015
@export var air_spread_transition := 10.0
@export var sprint_to_fire := 0.18

@export_group("音效")
@export var shoot_sound: AudioStream
@export var reload_sound: AudioStream
@export var kill_sound: AudioStream
