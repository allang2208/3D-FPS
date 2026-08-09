extends SceneTree
## 无头冒烟：旷野场景（demo_terrain）——传送点旁小鼠大王 NPC + 对话栏
## 运行：$godot --headless --path 'E:\3d\3-dfps' --script res://tests/test_demo_terrain.gd

const NpcConfig := preload("res://ui/npc_config.gd")

var _frame := 0
var _fail := 0
var _scene: Node
var _npc: Node
var _bar: Node

func _check(name: String, ok: bool, detail := "") -> void:
	print("TEST ", name, "=", ok, "" if detail.is_empty() else "  " + detail)
	if not ok:
		_fail += 1

func _initialize() -> void:
	var scene: PackedScene = load("res://scenes/demo_terrain.tscn")
	_scene = scene.instantiate()
	root.add_child(_scene)

func _process(_delta: float) -> bool:
	_frame += 1
	if _frame == 1:
		_run()
	return false

func _run() -> void:
	_npc = _scene.get_node_or_null("MouseKingNpc")
	_bar = _scene.get_node_or_null("NpcBar")
	_check("npc_exists", _npc != null)
	_check("npc_bar_exists", _bar != null)
	if _npc == null or _bar == null:
		quit(1)
		return
	var xz_ok: bool = Vector2(2.8, 26.0).distance_to(Vector2(_npc.position.x, _npc.position.z)) < 0.5
	var ground_y: float = float(_scene.get("terrain").data.get_height(Vector3(_npc.position.x, 0, _npc.position.z)))
	_check("npc_position_near_portal", xz_ok, "pos=" + str(_npc.position))
	_check("npc_on_ground", absf(float(_npc.position.y) - (ground_y + 0.9)) < 0.1,
		"y=%f ground=%f" % [_npc.position.y, ground_y])
	_check("npc_portrait_loaded", _npc.get("_sprite").texture != null)
	_check("npc_name_label", String(_npc.get("_name_label").text) == "小鼠大王")

	# 模拟玩家按 E：触发 interacted 信号 -> 打开对话栏
	_npc.interacted.emit(NpcConfig.NPCS["shop_mouse_king"])
	_check("bar_opened", bool(_bar.is_open()))
	_check("bar_name", String(_bar.get("_name_label").text) == "小鼠大王")
	_check("bar_portrait", bool(_bar.get("_portrait").texture != null))
	var want: Array = ["shop", "enhance", "craft", "enchant", "close"]
	_check("bar_options", _bar.get_option_ids() == want, "got=" + str(_bar.get_option_ids()))
	_npc.interacted.emit(NpcConfig.NPCS["shop_mouse_king"])
	_check("bar_toggle_closed", not bool(_bar.is_open()))
	quit(0 if _fail == 0 else 1)
