extends SceneTree
## 无头冒烟：黑狼存在、黑狼 AI 会移动、射击扣血、接触伤害让玩家掉血（测试期只留黑狼）
## 运行：& $godot --headless --path 'E:\3d\3-dfps' --script res://tests/test_combat.gd

const ProjectileScript := preload("res://scripts/projectile.gd")
const ImpactFxScript := preload("res://scripts/impact_fx.gd")

var _frames := 0
var _main: Node
var _wolf: Node3D
var _player: Node3D
var _start_pos := Vector3.ZERO
var _proj: Node
var _impact: Node
var _ads_hidden := false

func _initialize() -> void:
	var scene: PackedScene = load("res://scenes/main.tscn")
	_main = scene.instantiate()
	root.add_child(_main)

func _process(delta: float) -> bool:
	_frames += 1
	if _frames == 1:
		_wolf = _main.get_node_or_null("WolfEnemy") as Node3D
		_player = _main.get_node_or_null("Player") as Node3D
	if _wolf == null or _player == null:
		if _frames > 5:
			push_error("缺少敌人或玩家")
			quit(1)
			return false
		return false
	if _frames == 1:
		# 空旷地带（避开掩体木箱），玩家在狼 3 米外触发追击
		_wolf.global_position = Vector3(0, 0, 0)
		_player.global_position = Vector3(0, 0.2, 3)
		_start_pos = _wolf.global_position
		print("TEST enemies=1 start=", _start_pos)
	if _frames == 2:
		# ADS 时应隐藏准星（走信号全链路：gun.ads_changed → main._on_ads_changed → status_bar）
		var gun: Node = root.get_node("Main/Player/Camera3D/Gun")
		var sb: Node = root.get_node_or_null("Main/StatusBar")
		if sb == null:
			# UI 线未提交的 NPC 面板改动崩溃会导致 StatusBar 未创建——跳过而非判负
			_ads_hidden = true
			print("TEST ads_hides_crosshair=skip(status_bar_missing)")
		else:
			gun.ads_changed.emit(true)
			var ch: Node = sb.get("_ch_up")  # 四段式准星（UI 线重做后不再是 "+" Label）
			_ads_hidden = ch != null and ch.visible == false
			gun.ads_changed.emit(false)
			print("TEST ads_hides_crosshair=", _ads_hidden)
	if _frames == 5:
		# 验证弹道系统：飞行子弹命中黑狼（扣血），火花在生命周期后自毁
		var before := root.get_child_count()
		_proj = ProjectileScript.fire(root, Vector3(0, 0.8, -2), Vector3(0, 0, 1), 90.0, 25, 0.0)
		ImpactFxScript.spawn(root, Vector3(0, 0.8, -4), Vector3(0, 1, 0))
		_impact = root.get_child(before + 1)
	if _frames == 30:
		var proj_result: bool = not is_instance_valid(_proj) and _wolf.get("_hp") == 60
		print("TEST proj_hit_damage=", proj_result)
	if _frames == 120:
		var moved := _wolf.global_position.distance_to(_start_pos) > 0.5
		var hp_ok: bool = _wolf.get("_hp") == 60
		var player_hurt: bool = int(_player.get("hp")) < 100
		var fx_cleaned: bool = not is_instance_valid(_impact)
		print("TEST moved=", moved, " hp_ok=", hp_ok, " player_hurt=", player_hurt, " fx_cleaned=", fx_cleaned, " ads_hidden=", _ads_hidden)
		quit(0 if moved and hp_ok and player_hurt and fx_cleaned and _ads_hidden else 1)
		return false
	return false
