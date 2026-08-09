extends SceneTree
## 无头冒烟：加载主场景，验证黑狼 AI 会移动、take_damage 会扣血
## 运行：& $godot --headless --path 'E:\3d\3-dfps' --script res://tests/test_combat.gd

var _frames := 0
var _main: Node
var _wolf: Node3D
var _player: Node3D
var _start_pos := Vector3.ZERO

func _initialize() -> void:
	var scene: PackedScene = load("res://scenes/main.tscn")
	_main = scene.instantiate()
	root.add_child(_main)
	# 节点由 main.gd 的 _ready 构建，下一帧才可用

func _process(delta: float) -> bool:
	_frames += 1
	if _frames == 1:
		_wolf = _main.get_node_or_null("WolfEnemy") as Node3D
		_player = _main.get_node_or_null("Player") as Node3D
	if _wolf == null or _player == null:
		if _frames > 5:
			push_error("缺少 WolfEnemy 或 Player")
			quit(1)
			return false
		return true
	if _frames == 1:
		# 玩家放到黑狼 3 米外，触发追击
		_player.global_position = _wolf.global_position + Vector3(0, 0, 3)
		_start_pos = _wolf.global_position
		print("TEST start=", _start_pos)
	if _frames == 30:
		_wolf.call("take_damage", 25)
		print("TEST hp_after_shot=", _wolf.get("_hp"))
	if _frames == 90:
		var moved := _wolf.global_position.distance_to(_start_pos) > 0.5
		var hp_ok: bool = _wolf.get("_hp") == 60
		print("TEST moved=", moved, " hp_ok=", hp_ok)
		quit(0 if moved and hp_ok else 1)
		return false
	return false
