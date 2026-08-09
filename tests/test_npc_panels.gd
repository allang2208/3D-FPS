extends SceneTree
## 无头冒烟：NPC 子面板全量（商店/强化/改造/附魔/任务/祭品合成/出征）
## 运行：$godot --headless --path 'E:\3d\3-dfps' --script res://tests/test_npc_panels.gd

const NpcConfig := preload("res://ui/npc_config.gd")
const WeaponFormula := preload("res://ui/weapon_formula.gd")

var _db: RefCounted
var _bp: RefCounted
var _eq: RefCounted
var _econ: RefCounted
var _fail := 0
var _frame := 0
var _teleported := ""
var _departed: Array = []

func _check(name: String, ok: bool, detail := "") -> void:
	print("TEST ", name, "=", ok, "" if detail.is_empty() else "  " + detail)
	if not ok:
		_fail += 1

func _initialize() -> void:
	_db = load("res://ui/item_db.gd").new()
	_bp = load("res://ui/backpack.gd").new(_db)
	_eq = load("res://ui/equipment.gd").new(_bp)
	_econ = load("res://ui/economy.gd").new()
	_bp.add_item("rusty_sword", 1)
	_bp.add_item("g18_pistol", 1)
	_bp.add_item("enhancement_stone", 2)
	_bp.add_item("reforge_ticket", 2)
	_bp.add_item("magic_dust", 150)
	_bp.add_item("enchant_scroll_heavy", 1)
	_bp.add_item("enchant_scroll_tarantula", 1)
	_bp.add_item("tribute_common", 4)
	_bp.add_item("tribute_uncommon", 2)

func _process(_delta: float) -> bool:
	_frame += 1
	if _frame == 1:
		_run()
	return false

func _slot_of(id: String) -> int:
	for i in _bp.slots.size():
		if _bp.slots[i] != null and String(_bp.slots[i].get("id", "")) == id:
			return i
	return -1

func _run() -> void:
	# 商店：买 rusty_sword（100） -> 卖出（50）
	var shop = load("res://ui/shop_panel.gd").new()
	root.add_child(shop)
	shop.setup(_db, _bp, _eq, _econ)
	shop.open_panel()
	shop._buy("rusty_sword", 100)
	_check("shop_buy_gold", int(_econ.get_gold()) == 4900, "gold=" + str(_econ.get_gold()))
	var rs := _slot_of("rusty_sword")
	_check("shop_buy_added", rs >= 0)
	shop._add_to_sell(rs)
	_check("shop_sell_moved", _slot_of("rusty_sword") == -1 and shop._sell.size() == 1)
	shop._confirm_sell()
	_check("shop_sell_gold", int(_econ.get_gold()) == 4950, "gold=" + str(_econ.get_gold()))
	shop.close()

	# 强化：放 rusty_sword（需要先买回） -> +1
	shop.setup(_db, _bp, _eq, _econ)
	shop.open_panel()
	shop._buy("rusty_sword", 100)
	shop.close()
	var enhance = load("res://ui/enhance_panel.gd").new()
	root.add_child(enhance)
	enhance.setup(_db, _bp, _eq, _econ)
	enhance.open_panel()
	rs = _slot_of("rusty_sword")
	enhance._equip_from_backpack(rs)
	enhance._enhance()
	var e_item: Dictionary = enhance._equipped["item"]
	_check("enhance_level", int(e_item.get("enhanceLevel", 0)) == 1)
	_check("enhance_gold", int(_econ.get_gold()) == 4750, "gold=" + str(_econ.get_gold()))
	_check("enhance_stone", _slot_of("enhancement_stone") == -1 or int(_bp.slots[_slot_of("enhancement_stone")].get("stack", 0)) == 1)
	enhance._return_item()
	rs = _slot_of("rusty_sword")
	_check("enhance_returned", rs >= 0 and int(_bp.slots[rs].get("enhanceLevel", 0)) == 1)
	enhance.close()

	# 改造：g18_pistol 装 auto_trigger（1 张票）
	var craft = load("res://ui/craft_panel.gd").new()
	root.add_child(craft)
	craft.setup(_db, _bp, _eq, _econ)
	craft.open_panel()
	var g18 := _slot_of("g18_pistol")
	craft._equip_from_backpack(g18)
	var craft_cfg: Dictionary = NpcConfig.craft_config_for(craft._equipped["item"])
	var slot_id := String(craft_cfg["slots"][0]["id"])
	var mod_id := String(craft_cfg["options"][slot_id][0]["id"])
	craft._equip_mod(slot_id, mod_id)
	var c_item: Dictionary = craft._equipped["item"]
	var c_data: Dictionary = c_item.get("_craftData", {})
	_check("craft_data", String(c_data.get(slot_id, "")) == mod_id)
	_check("craft_effects", not c_item.get("_craftEffects", {}).is_empty())
	_check("craft_ticket", _slot_of("reforge_ticket") == -1 or int(_bp.slots[_slot_of("reforge_ticket")].get("stack", 0)) == 1)
	craft._enter_edit()
	var layout_edit_ok: bool = craft._layout != null and bool(craft._layout.editing)
	craft._cancel_edit()
	var layout_cancel_ok: bool = craft._layout != null and not bool(craft._layout.editing)
	_check("craft_layout_edit_cancel", layout_edit_ok and layout_cancel_ok)
	craft._return_item()
	craft.close()

	# 附魔：沉重（近战剑，100 粉尘） + 卷轴转粉尘
	var enchant = load("res://ui/enchant_panel.gd").new()
	root.add_child(enchant)
	enchant.setup(_db, _bp, _eq, _econ)
	enchant.open_panel()
	var scroll_slot := _slot_of("enchant_scroll_heavy")
	rs = _slot_of("rusty_sword")
	enchant._place_scroll("backpack", scroll_slot)
	enchant._place_equip("backpack", rs)
	_check("enchant_compatible", not enchant._enchant_btn.disabled)
	enchant._do_enchant()
	var e2: Dictionary = enchant._equip
	_check("enchant_prefix", String(e2.get("_enchantData", {}).get("prefix", {}).get("name", "")) == "沉重")
	_check("enchant_dust", int(enchant._count_dust()) == 50, "dust=" + str(enchant._count_dust()))
	enchant._return_equip()
	var ts := _slot_of("enchant_scroll_tarantula")
	enchant._place_scroll("backpack", ts)
	enchant._convert_dust()
	_check("enchant_convert_dust", int(enchant._count_dust()) == 150, "dust=" + str(enchant._count_dust()))
	enchant.close()

	# 任务：接受 + 传送信号
	var quest = load("res://ui/quest_panel.gd").new()
	root.add_child(quest)
	quest.setup(_db, _bp, _eq, _econ)
	quest.teleport_requested.connect(func(id): _teleported = id)
	quest.open_panel()
	quest._accept()
	_check("quest_accepted", bool(quest._quests["explore_rift_1"].get("accepted", false)))
	quest._teleport_btn.pressed.emit()
	_check("quest_teleport_signal", _teleported == "explore_rift_1")
	quest.close()

	# 祭品合成：2 个普通 -> 1 个优质
	var fusion = load("res://ui/fusion_panel.gd").new()
	root.add_child(fusion)
	fusion.setup(_db, _bp, _eq, _econ)
	fusion.open_panel()
	var t1 := _slot_of("tribute_common")
	fusion._place_from_backpack(t1)
	var t2 := _slot_of("tribute_common")
	fusion._place_from_backpack(t2)
	fusion._fuse()
	var result_rarity := ""
	for entry in fusion._placed:
		if entry != null:
			result_rarity = String(entry["item"].get("rarity", ""))
			break
	_check("fusion_result", result_rarity == "uncommon", "got=" + result_rarity)
	fusion.close()

	# 出征：放入 1 普通祭品 -> depart 信号（返回后返还）
	var exp = load("res://ui/expedition_panel.gd").new()
	root.add_child(exp)
	exp.setup(_db, _bp, _eq, _econ)
	exp.depart_requested.connect(func(items):
		_departed = items
		for it in items:
			_bp.add_item(String(it.get("id", "")), 1))
	exp.open_panel()
	var t3 := _slot_of("tribute_common")
	exp._place_from_backpack(t3)
	exp._depart()
	_check("expedition_departed", _departed.size() == 1, "n=" + str(_departed.size()))
	_check("expedition_returned", _slot_of("tribute_common") >= 0)
	exp.close()

	# 改造配置全量覆盖（craft-config.json 17 把）
	var craft_keys: Array = [
		"weapon2", "weapon4", "weapon5", "weapon6", "weapon7", "weapon8", "weapon9",
		"weapon10", "weapon11", "weapon12", "weapon13", "weapon15", "weapon18",
		"weapon19", "weapon20", "weapon21", "weapon22",
	]
	var craft_all := true
	for k in craft_keys:
		if NpcConfig.get_craft_config(String(k)).is_empty():
			craft_all = false
	_check("craft_config_17", craft_all)
	_check("craft_config_akm", not NpcConfig.get_craft_config("weapon7").is_empty())

	# 武器攻击公式（attack-formula.js 对齐）：base5 + 3 + dex10*(0.35+0.45) + wis10*(0.4+0.45) = 25
	var atk := WeaponFormula.compute_weapon_atk({
		"attackFormula": {"base": 5, "enhanceFlat": 1, "attrs": [
			{"key": "dex", "base": 0.35, "perEnhance": 0.15},
			{"key": "wis", "base": 0.4, "perEnhance": 0.15},
		]},
	}, 3, {"dex": 10, "wis": 10})
	_check("weapon_formula", atk == 25, "atk=" + str(atk))

	# 仓库兜底：背包无强化石 -> 从仓库扣（当前 rusty_sword 已 +1，再强化到 +2）
	var wh = load("res://ui/warehouse.gd").new()
	wh.add_item(_db.create_instance("enhancement_stone", 1))
	enhance.set_warehouse(wh)
	var st := _slot_of("enhancement_stone")
	if st >= 0:
		_bp.slots[st] = null
	enhance._equip_from_backpack(_slot_of("rusty_sword"))
	var gold_before := int(_econ.get_gold())
	enhance._enhance()
	_check("enhance_warehouse_stone",
		int(_econ.get_gold()) < gold_before and int(enhance._equipped["item"].get("enhanceLevel", 0)) == 2)
	_check("warehouse_consumed",
		wh.count_material(func(i): return String(i.get("id", "")) == "enhancement_stone") == 0)
	enhance._return_item()

	# 仓库不叠武器（旧版默认 maxStack=1）
	var wh2 = load("res://ui/warehouse.gd").new()
	wh2.add_item(_db.create_instance("rusty_sword", 1))
	wh2.add_item(_db.create_instance("rusty_sword", 1))
	_check("warehouse_no_weapon_stack",
		wh2.items.size() == 2 and int(wh2.items[0].get("stack", 0)) == 1,
		"n=" + str(wh2.items.size()))

	quit(0 if _fail == 0 else 1)
