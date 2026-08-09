extends SceneTree
## 无头验证背包栏迁移：物品堆叠/使用回血/快捷栏绑定与回退/面板开关/HUD 接线
## 运行：$godot --headless --path 'E:\3d\3-dfps' --script res://tests/test_backpack.gd

const ItemDbScript := preload("res://ui/item_db.gd")
const BackpackScript := preload("res://ui/backpack.gd")

class StubPlayer:
	var hp := 100
	var max_hp := 200
	var mp := 0
	var is_dead := false
	func heal(amount: int) -> void:
		hp = mini(max_hp, hp + amount)
	func add_mp(amount: int) -> void:
		mp = mini(100, mp + amount)

var _fail := 0
var _frames := 0
var _stage := 0
var _stage_start := 0
var _main: Node
var _hud: Node
var _player: Node
var _bar: Node

func _check(name: String, ok: bool) -> void:
	print("TEST ", name, "=", ok)
	if not ok:
		_fail += 1

func _initialize() -> void:
	_data_tests()
	var scene: PackedScene = load("res://scenes/main.tscn")
	_main = scene.instantiate()
	root.add_child(_main)
	current_scene = _main

func _process(_delta: float) -> bool:
	_frames += 1
	if _stage == 0:
		_stage = 1
		_hud = _main.get_node_or_null("StatusBar/BackpackHud")
		_player = _main.get_node_or_null("Player")
		_bar = _main.get_node_or_null("StatusBar")
		_check("hud_wired", _hud != null and _player != null and _bar != null)
		if _hud == null or _player == null or _bar == null:
			quit(1)
			return false
		_player.set("hp", 100000)
		var bp = _hud.get("backpack")
		_check("seed_items", bp.item_count() == 5 and int(bp.slots[0].get("stack", 0)) == 5)
		# 受击后用药回血 → 状态栏生命恢复，且不触发受伤红闪
		_player.set("hp", 70)
		bp.bind_hotbar(0, String(bp.slots[0].get("instance_id", "")))
		_hud.use_hotbar(0)
		_check("heal_updates_hud", int(_player.get("hp")) == 100 \
			and String(_bar.get("_hp_label").text).contains("100/100"))
		_check("heal_no_damage_flash", float(_bar.get("_dmgflash_t")) == 0.0)
		# 魔力药水：玩家无 MP 接口 → 不可用且不消耗
		bp.add_item("mp_potion", 1)
		var mp_inst := String(bp.slots[1].get("instance_id", ""))
		var mp_result = bp.use_item(mp_inst, _player)
		_check("mp_unavailable", not mp_result.get("ok", false) and bp.slots[1] != null)
		# 面板开关
		_hud.toggle_panel()
		_check("panel_open", bool(_hud.get("_panel_open")) and bool(_hud.get("_panel_root").visible))
		_hud.toggle_panel()
		_check("panel_close", not bool(_hud.get("_panel_open")))
		# 浮窗 / 毛玻璃 / 满包提示
		_check("tooltip_built", _hud.get("_tooltip") != null)
		_hud.show_item_tooltip(bp.slots[0], Vector2(120, 120))
		_check("tooltip_show", bool(_hud.get("_tooltip").visible))
		_check("panel_blur", _hud.get("_panel").get_node("Content/Blur").material != null)
		# 拖拽落点：背包格→快捷栏绑定；快捷栏→快捷栏交换；快捷栏→背包格解绑
		bp.bind_hotbar(1, String(bp.slots[0].get("instance_id", "")))
		_hud.drop_on_hotbar(2, {"type": "backpack", "slot": 0})
		_check("drop_bind", bp.hotbar[2] != null)
		var hp_inst := String(bp.slots[0].get("instance_id", ""))
		bp.bind_hotbar(1, mp_inst)
		_hud.drop_on_hotbar(2, {"type": "hotbar", "index": 1})
		_check("drop_swap", bp.hotbar[1] != null and bp.hotbar[2] != null \
			and bp.hotbar[1].get("instance_id", "") == hp_inst \
			and bp.hotbar[2].get("instance_id", "") == mp_inst)
		_hud.drop_on_backpack(3, {"type": "hotbar", "index": 1})
		_check("drop_unbind", bp.hotbar[1] == null)
		# 背包填满后 try_add 返回 false 并弹出"背包已满"提示
		var fills := 0
		while fills < 100:
			if not _hud.try_add("hp_potion", 5):
				break
			fills += 1
		_check("notice_full", bool(_hud.get("_notice_label").visible) \
			and String(_hud.get("_notice_label").text).contains("背包已满"))
		# 打开面板等滑入动画结束，验证面板完全在 1280x720 视口内
		_hud.toggle_panel()
		_stage = 2
		_stage_start = Time.get_ticks_msec()
	elif _stage == 2 and Time.get_ticks_msec() - _stage_start > 800:
		var panel: Control = _hud.get("_panel")
		var r := panel.get_global_rect()
		var vp := Rect2(Vector2.ZERO, root.get_visible_rect().size)
		_check("panel_on_screen", vp.encloses(r))
		_check("panel_right_aligned", absf(r.end.x - vp.size.x) < 2.0 and r.position.x > 0.0)
		print("TEST panel_rect=", r, " viewport=", vp.size)
		quit(0 if _fail == 0 else 1)
	return false

func _data_tests() -> void:
	var db := ItemDbScript.new()
	var bp := BackpackScript.new(db)
	_check("db_hp_potion", db.has_item("hp_potion"))
	_check("db_mp_potion", db.has_item("mp_potion"))
	_check("slots_36", bp.slots.size() == 36)
	_check("hotbar_4", bp.hotbar.size() == 4)
	_check("add_2", bp.add_item("hp_potion", 2))
	_check("count_2", bp.item_count() == 1 and int(bp.slots[0].get("stack", 0)) == 2)
	_check("stack_to_4", bp.add_item("hp_potion", 2) and int(bp.slots[0].get("stack", 0)) == 4)
	_check("stack_to_second_slot", bp.add_item("hp_potion", 2) \
		and int(bp.slots[0].get("stack", 0)) == 5 and int(bp.slots[1].get("stack", 0)) == 1)
	var inst0 := String(bp.slots[0].get("instance_id", ""))
	var inst1 := String(bp.slots[1].get("instance_id", ""))
	_check("bind_ok", bp.bind_hotbar(0, inst0))
	_check("bind_unknown_rejected", not bp.bind_hotbar(1, "nope"))
	# 信号：item_added / bound
	var added_slots := []
	var bound_indexes := []
	bp.item_added.connect(func(s: int) -> void: added_slots.append(s))
	bp.bound.connect(func(i: int) -> void: bound_indexes.append(i))
	bp.add_item("hp_potion", 1)
	_check("signal_item_added", not added_slots.is_empty())
	bp.bind_hotbar(0, inst0)
	_check("signal_bound", not bound_indexes.is_empty() and int(bound_indexes[0]) == 0)
	var stub := StubPlayer.new()
	var use0 := bp.use_hotbar(0, stub)
	_check("use_heal", use0.get("ok", false) and stub.hp == 130)
	_check("use_consumes", int(bp.slots[0].get("stack", 0)) == 4)
	_check("add_mp", bp.add_item("mp_potion", 1))
	var inst_mp := String(bp.slots[2].get("instance_id", ""))
	_check("use_mp", bp.use_item(inst_mp, stub).get("ok", false) and stub.mp == 25)
	# 冷却：useCooldown 生效、期间拦截、到期恢复
	bp.slots[0]["useCooldown"] = 0.4
	bp.bind_hotbar(1, inst0)
	_check("cd_use_ok", bp.use_hotbar(1, stub).get("ok", false))
	var cd2 := bp.use_hotbar(1, stub)
	_check("cd_blocked", not cd2.get("ok", false) and cd2.get("cooldown", false))
	bp.tick_cooldowns(0.5)
	_check("cd_expired", bp.use_hotbar(1, stub).get("ok", false))
	# 交换后绑定仍按实例解析
	bp.swap_items(0, 1)
	_check("swap_updates_slot", bp.slots[0] != null and bp.slots[1] != null \
		and String(bp.slots[0].get("instance_id", "")) == inst1 \
		and String(bp.slots[1].get("instance_id", "")) == inst0)
	_check("swap_keeps_binding", not bp.resolve_hotbar(0).is_empty())
	# 用完最后一瓶：快捷栏绑定保留，数量回退为 0/按名称找回新物品
	var bp2 := BackpackScript.new(db)
	bp2.add_item("hp_potion", 1)
	var inst_a := String(bp2.slots[0].get("instance_id", ""))
	bp2.bind_hotbar(0, inst_a)
	_check("exhaust_ok", bp2.use_hotbar(0, stub).get("ok", false))
	_check("exhaust_removes_item", bp2.slots[0] == null)
	_check("exhaust_keeps_binding", bp2.hotbar[0] != null)
	_check("exhaust_resolve_empty", bp2.resolve_hotbar(0).is_empty())
	bp2.add_item("hp_potion", 2)
	_check("restock_fallback", not bp2.resolve_hotbar(0).is_empty() \
		and int(bp2.resolve_hotbar(0).get("stack", 0)) == 2)
	# 所有堆叠填满后背包拒绝新物品
	while bp.add_item("hp_potion", 5):
		pass
	_check("full_rejects", not bp.add_item("hp_potion", 1))
