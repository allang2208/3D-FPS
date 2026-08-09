extends SceneTree
## 无头验证装备栏迁移：装备/卸下/双手锁定/交换规则 + HUD 装备页接线与浮窗
## 运行：$godot --headless --path 'E:\3d\3-dfps' --script res://tests/test_equip.gd

const ItemDbScript := preload("res://ui/item_db.gd")
const BackpackScript := preload("res://ui/backpack.gd")
const EquipmentScript := preload("res://ui/equipment.gd")

var _fail := 0
var _stage := 0
var _stage_start := 0
var _main: Node
var _hud: Node

func _check(name: String, ok: bool) -> void:
	print("TEST ", name, "=", ok)
	if not ok:
		_fail += 1

func _find_slot(bp, id: String) -> int:
	for i in bp.slots.size():
		if bp.slots[i] != null and String(bp.slots[i].get("id", "")) == id:
			return i
	return -1

func _initialize() -> void:
	_data_tests()
	var scene: PackedScene = load("res://scenes/main.tscn")
	_main = scene.instantiate()
	root.add_child(_main)
	current_scene = _main

func _process(_delta: float) -> bool:
	if _stage == 0:
		_stage = 1
		_hud = _main.get_node_or_null("StatusBar/BackpackHud")
		_check("equip_hud_wired", _hud != null and _hud.get("equipment") != null)
		if _hud == null or _hud.get("equipment") == null:
			quit(1)
			return false
		var eq = _hud.get("equipment")
		var bp = _hud.get("backpack")
		_check("equip_seed", String(eq.get_item("weapon").get("name", "")) == "生锈的长剑")
		var icon_path := String(eq.get_item("weapon").get("icon", ""))
		_check("equip_icon_migrated", icon_path != "" and ResourceLoader.exists(icon_path))
		_check("equip_grid_15", int(_hud.get("_equip_grid").get_child_count()) == 15)
		_check("inv_grid_36", int(_hud.get("_grid").get_child_count()) == 36)
		# 拖放：背包 G18 → weapon2
		var g18_slot := -1
		for i in bp.slots.size():
			if bp.slots[i] != null and String(bp.slots[i].get("id", "")) == "g18_pistol":
				g18_slot = i
				break
		_hud.drop_on_equip("weapon2", {"type": "backpack", "slot": g18_slot})
		_check("drop_equip_g18", String(eq.get_item("weapon2").get("name", "")) == "G18")
		# 双手武器（训练用弓）拖到 weapon → 替换长剑并锁定 offhand
		_hud.try_add("training_bow", 1)
		var bow_slot := -1
		for i in bp.slots.size():
			if bp.slots[i] != null and String(bp.slots[i].get("id", "")) == "training_bow":
				bow_slot = i
				break
		_hud.drop_on_equip("weapon", {"type": "backpack", "slot": bow_slot})
		_check("drop_equip_bow", String(eq.get_item("weapon").get("name", "")) == "训练用弓")
		_check("lock_offhand", bool(eq.is_locked("offhand")))
		_check("lock_visual", bool(_hud.get("_equip_cells")["offhand"].get_node("Content/Lock").visible))
		# 右键卸下 weapon2（G18 回背包）
		_hud.on_equip_right_click("weapon2")
		_check("right_click_unequip", eq.get_item("weapon2").is_empty() and bp.item_count() >= 4)
		# 装备浮窗：显示名称 + 稀有度
		_hud.show_item_tooltip(eq.get_item("weapon"), Vector2(120, 120))
		_check("tooltip_equip_name", String(_hud.get("_tooltip").get("_name_label").text) == "训练用弓")
		_check("tooltip_equip_rarity", int(_hud.get("_tooltip").get("_type_row").get_child_count()) >= 2)
		_stage = 2
		_stage_start = Time.get_ticks_msec()
	elif _stage == 2 and Time.get_ticks_msec() - _stage_start > 600:
		quit(0 if _fail == 0 else 1)
	return false

func _data_tests() -> void:
	var db := ItemDbScript.new()
	var bp := BackpackScript.new(db)
	var eq := EquipmentScript.new(bp)
	_check("slots_15", eq.SLOT_ORDER.size() == 15)
	_check("load_equipment_db", db.has_item("rusty_sword") and db.has_item("training_bow") and db.has_item("lunar_helmet"))
	# 单手剑 → weapon
	bp.add_item("rusty_sword", 1)
	_check("equip_sword", eq.equip_from_backpack(0) and String(eq.get_item("weapon").get("name", "")) == "生锈的长剑")
	_check("removed_from_backpack", bp.slots[0] == null)
	# 单手枪 → 主手已占用 → offhand
	bp.add_item("g18_pistol", 1)
	_check("equip_g18_offhand", eq.equip_from_backpack(0) and String(eq.get_item("offhand").get("name", "")) == "G18")
	# 双手弓 → weapon2
	bp.add_item("training_bow", 1)
	_check("equip_bow_weapon2", eq.equip_from_backpack(0) and String(eq.get_item("weapon2").get("name", "")) == "训练用弓")
	_check("lock_ring2", eq.is_locked("ring2"))
	_check("not_lock_offhand", not eq.is_locked("offhand"))
	# 盾 → offhand（weapon 单手不冲突）
	bp.add_item("small_shield", 1)
	_check("equip_shield", eq.equip_from_backpack(0) and String(eq.get_item("offhand").get("name", "")) == "小圆盾")
	# 双手弓拖到 weapon → 卸下 offhand 盾并锁定
	bp.add_item("training_bow", 1)
	_check("equip_bow_weapon", eq.equip_to_slot("weapon", _find_slot(bp, "training_bow")) \
		and String(eq.get_item("weapon").get("name", "")) == "训练用弓" \
		and eq.get_item("offhand").is_empty() and eq.is_locked("offhand"))
	# 卸下回背包
	_check("unequip_returns", eq.unequip("weapon") and eq.get_item("weapon").is_empty() and bp.item_count() >= 1)
	# 交换
	bp.add_item("knights_sword", 1)
	_check("equip_knights", eq.equip_to_slot("weapon", _find_slot(bp, "knights_sword")))
	bp.add_item("night_flame_sword", 1)
	_check("equip_nightflame", eq.equip_to_slot("offhand", _find_slot(bp, "night_flame_sword")))
	_check("swap_equip", eq.swap_equip("weapon", "offhand") and String(eq.get_item("weapon").get("name", "")) == "夜与火之剑")
	# 兼容性判定
	bp.add_item("lunar_helmet", 1)
	var helmet: Dictionary = bp.slots[_find_slot(bp, "lunar_helmet")]
	_check("can_equip_helmet", eq.can_equip_to("helmet", helmet))
	_check("reject_helmet_to_weapon", not eq.can_equip_to("weapon", helmet))
