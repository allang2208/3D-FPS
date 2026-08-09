extends SceneTree
## 无头冒烟：三只敌人存在、黑狼 AI 会移动、射击扣血、接触伤害让玩家掉血
## 运行：& $godot --headless --path 'E:\3d\3-dfps' --script res://tests/test_combat.gd

const ProjectileScript := preload("res://scripts/projectile.gd")
const ImpactFxScript := preload("res://scripts/impact_fx.gd")

var _frames := 0
var _main: Node
var _wolf: Node3D
var _dog: Node3D
var _spider: Node3D
var _player: Node3D
var _start_pos := Vector3.ZERO
var _proj: Node
var _impact: Node

func _initialize() -> void:
	var scene: PackedScene = load("res://scenes/main.tscn")
	_main = scene.instantiate()
	root.add_child(_main)

func _process(delta: float) -> bool:
	_frames += 1
	if _frames == 1:
		_wolf = _main.get_node_or_null("WolfEnemy") as Node3D
		_dog = _main.get_node_or_null("ZombieDog") as Node3D
		_spider = _main.get_node_or_null("Spider") as Node3D
		_player = _main.get_node_or_null("Player") as Node3D
	if _wolf == null or _dog == null or _spider == null or _player == null:
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
		print("TEST enemies=3 start=", _start_pos)
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
		print("TEST moved=", moved, " hp_ok=", hp_ok, " player_hurt=", player_hurt, " fx_cleaned=", fx_cleaned)
		quit(0 if moved and hp_ok and player_hurt and fx_cleaned else 1)
		return false
	return false
