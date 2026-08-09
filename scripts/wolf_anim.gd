extends Node3D
## Quaternius 动画狼驱动：enemy.gd 的 rig_update 接口 → AnimationPlayer 状态机
## 资产：CC0 Quaternius 动画狼（Attack/Death/Gallop/Idle/Walk/HitReact 等 12 条关键帧）
## 状态映射：moving→Gallop，待机→Idle，扑咬窗口→Attack（加速播），dead→Death（单次）

var no_death_flip := true  # 有真正的死亡动画，enemy.gd 不要再做节点级翻倒/下沉

const LOOP_ANIMS := ["Idle", "Idle_2", "Idle_2_HeadLow", "Walk", "Gallop", "Eating"]
const ATTACK_SPEED := 2.5  # Attack 原长 1.33s，加速贴合 0.25s 扑咬窗口

var _ap: AnimationPlayer
var _state := ""

func _ready() -> void:
	_ap = find_child("AnimationPlayer", true, false)
	_play("Idle")

func rig_update(_t: float, moving: bool, attack_t: float, dead: bool) -> void:
	if _ap == null:
		return
	if dead:
		_play("Death")
		return
	if attack_t > 0.0:
		_play("Attack")
		_ap.speed_scale = ATTACK_SPEED
		return
	_ap.speed_scale = 1.0
	_play("Gallop" if moving else "Idle")

func rig_reset() -> void:
	_ap.speed_scale = 1.0
	_state = ""
	_play("Idle")

func _play(anim_name: String) -> void:
	if _ap == null:
		return
	var anim := _ap.get_animation(anim_name)
	if anim == null:
		return
	anim.loop_mode = Animation.LOOP_LINEAR if anim_name in LOOP_ANIMS else Animation.LOOP_NONE
	if _state == anim_name:
		return
	_state = anim_name
	_ap.play(anim_name)
