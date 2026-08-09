extends Node3D
## Quaternius 人形僵尸驱动：enemy.gd 的 rig_update 接口 → AnimationPlayer 状态机
## 资产：CC0 Quaternius Zombie（Zombie Apocalypse Kit），16 条关键帧 + Atlas 贴图
## 状态映射：追击→Run_Arms（举手扑跑），游荡→Walk，待机→Idle，扑咬窗口→Punch（加速），dead→Death

var no_death_flip := true  # 有真正的死亡动画，enemy.gd 不要再做节点级翻倒/下沉

const LOOP_ANIMS := ["Idle", "Walk", "Run_Arms", "Crawl", "Run", "Run_Attack"]
const ATTACK_SPEED := 2.5  # 贴合 enemy.gd 的 0.25s 扑咬窗口

var _ap: AnimationPlayer
var _state := ""

func _ready() -> void:
	_ap = find_child("AnimationPlayer", true, false)
	_play("Idle")

## chasing=false 的 moving 是游荡（慢），用 Walk；追击用 Run_Arms
func rig_update(_t: float, moving: bool, attack_t: float, dead: bool, chasing := true) -> void:
	if _ap == null:
		return
	if dead:
		_play("Death")
		return
	if attack_t > 0.0:
		_play("Punch")
		_ap.speed_scale = ATTACK_SPEED
		return
	_ap.speed_scale = 1.0
	if not moving:
		_play("Idle")
	elif chasing:
		_play("Run_Arms")
	else:
		_play("Walk")

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
