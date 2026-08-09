extends "res://ui/npc_panel.gd"
## 强化面板（enhance-system.js 迁移）：放入装备 -> 消耗金币 + 强化石 -> +1 强化等级。
## 强化上限：武器（含盾）15 级，其他装备 10 级；费用 = baseCost * costGrowth^level。

const NpcConfig := preload("res://ui/npc_config.gd")
const WeaponFormula := preload("res://ui/weapon_formula.gd")

var _db: RefCounted
var _equipment: RefCounted
var _warehouse: RefCounted
var _player_status
var _equipped := {}  # {item, source, slot}

var _slot_label: Label
var _info_label: Label
var _cost_label: Label
var _bp_grid: GridContainer
var _eq_grid: GridContainer
var _circle_icon: Label
var _circle_glow: Panel
var _glow_t := 0.0

func _process(delta: float) -> void:
	super._process(delta)
	if not is_open():
		return
	if _circle_icon == null:
		return
	_glow_t += delta
	_circle_icon.rotation = _glow_t * 0.4
	if _circle_glow != null:
		_circle_glow.modulate.a = 0.30 + 0.22 * (0.5 + 0.5 * sin(_glow_t * 2.2))

func setup(db: RefCounted, backpack: RefCounted, equipment: RefCounted, economy: RefCounted) -> void:
	_db = db
	_backpack = backpack
	_equipment = equipment
	set_economy(economy)
	if _backpack != null and not _backpack.changed.is_connected(_on_changed):
		_backpack.changed.connect(_on_changed)

func set_warehouse(wh: RefCounted) -> void:
	_warehouse = wh

func set_player_status(ps) -> void:
	_player_status = ps

func _build_body() -> void:
	# 魔法阵（旧版 magic-circle-container：金色圆环装饰 + 槽位信息）
	var circle_row := HBoxContainer.new()
	circle_row.add_theme_constant_override("separation", 14)
	body.add_child(circle_row)
	_circle_glow = Panel.new()
	_circle_glow.custom_minimum_size = Vector2(96, 96)
	_circle_glow.add_theme_stylebox_override("panel",
		Style.make_style(Color(Style.THEME_GOLD, 0.35), Color(Style.THEME_GOLD, 0.0), 48, 0))
	circle_row.add_child(_circle_glow)
	var circle := Panel.new()
	circle.custom_minimum_size = Vector2(96, 96)
	circle.add_theme_stylebox_override("panel",
		Style.make_style(Color(Style.THEME_BG, 0.0), Style.THEME_GOLD, 48, 2))
	circle.position = Vector2(0, 0)
	circle.size = Vector2(96, 96)
	_circle_glow.add_child(circle)
	_circle_icon = Label.new()
	_circle_icon.text = "⚒️"
	_circle_icon.add_theme_font_size_override("font_size", 36)
	_circle_icon.set_anchors_and_offsets_preset(Control.PRESET_CENTER)
	circle.add_child(_circle_icon)
	var slot_drop := _make_drop_slot()
	slot_drop.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	circle_row.add_child(slot_drop)
	var slot_box := VBoxContainer.new()
	slot_box.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	slot_box.add_theme_constant_override("separation", 4)
	slot_box.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	slot_drop.add_child(slot_box)
	_slot_label = _make_label("强化槽：拖入装备", "body", Style.THEME_GRAY_LIGHT)
	slot_box.add_child(_slot_label)
	_info_label = _make_label("", "body", Style.THEME_WHITE)
	slot_box.add_child(_info_label)
	_cost_label = _make_label("", "body", Style.THEME_GOLD)
	slot_box.add_child(_cost_label)
	slot_drop.dropped.connect(_on_drop_equip)

	var actions := HBoxContainer.new()
	actions.add_theme_constant_override("separation", Style.spacing("element_gap"))
	body.add_child(actions)
	var enhance_btn := _make_button("✨ 强化")
	enhance_btn.pressed.connect(_enhance)
	actions.add_child(enhance_btn)
	var remove_btn := _make_button("↔ 取下")
	remove_btn.pressed.connect(_return_item)
	actions.add_child(remove_btn)

	var h := HBoxContainer.new()
	h.size_flags_vertical = Control.SIZE_EXPAND_FILL
	h.add_theme_constant_override("separation", Style.spacing("element_gap"))
	body.add_child(h)

	var bp_col := VBoxContainer.new()
	bp_col.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	bp_col.add_theme_constant_override("separation", Style.spacing("grid"))
	h.add_child(bp_col)
	bp_col.add_child(_make_section_title("🎒 背包"))
	var bp_scroll := ScrollContainer.new()
	bp_scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	bp_col.add_child(bp_scroll)
	_bp_grid = GridContainer.new()
	_bp_grid.columns = 3
	_bp_grid.add_theme_constant_override("h_separation", 6)
	_bp_grid.add_theme_constant_override("v_separation", 6)
	bp_scroll.add_child(_bp_grid)

	var eq_col := VBoxContainer.new()
	eq_col.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	eq_col.add_theme_constant_override("separation", Style.spacing("grid"))
	h.add_child(eq_col)
	eq_col.add_child(_make_section_title("⚒️ 已装备"))
	var eq_scroll := ScrollContainer.new()
	eq_scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	eq_col.add_child(eq_scroll)
	_eq_grid = GridContainer.new()
	_eq_grid.columns = 3
	_eq_grid.add_theme_constant_override("h_separation", 6)
	_eq_grid.add_theme_constant_override("v_separation", 6)
	eq_scroll.add_child(_eq_grid)

func _refresh() -> void:
	_refresh_gold()
	if _equipped.is_empty():
		_slot_label.text = "强化槽：拖入装备"
		_info_label.text = "请将装备拖入上方强化槽"
		_cost_label.text = "强化费用: 💰 0"
	else:
		var item: Dictionary = _equipped["item"]
		var level := int(item.get("enhanceLevel", 0))
		var max_level := NpcConfig.enhance_max_level(item)
		_slot_label.text = "强化槽：%s  +%d" % [String(item.get("name", "?")), level]
		_info_label.text = "当前强化等级：+%d / +%d\n%s" % [level, max_level, _predicted(item)]
		if level >= max_level:
			_cost_label.text = "已到达最高强化等级"
		else:
			_cost_label.text = "强化费用: 💰 %d + 💎 强化石×1" % NpcConfig.enhance_cost(level)
	_rebuild_grids()

func _rebuild_grids() -> void:
	for c in _bp_grid.get_children():
		c.queue_free()
	for i in _backpack.slots.size():
		var it = _backpack.slots[i]
		if it == null or it.is_empty() or String(it.get("category", "")) == "gold":
			continue
		var cell := _make_item_cell(it, Vector2(130, 52))
		cell.pressed.connect(func(_c, _idx: int = i): _equip_from_backpack(_idx))
		_bp_grid.add_child(cell)
	for c in _eq_grid.get_children():
		c.queue_free()
	for key in _equipment.SLOT_ORDER:
		var it = _equipment.slots.get(key, {})
		if it == null or it.is_empty():
			continue
		var cell := _make_item_cell(it, Vector2(130, 52))
		cell.pressed.connect(func(_c, _key: String = String(key)): _equip_from_slot(_key))
		_eq_grid.add_child(cell)

func _equip_from_backpack(slot: int) -> void:
	var it = _backpack.slots[slot]
	if it == null or it.is_empty() or String(it.get("category", "")) == "gold":
		return
	_return_item()
	_backpack.slots[slot] = null
	_equipped = {"item": it, "source": "backpack", "slot": slot}
	_backpack.changed.emit()
	_refresh()

func _equip_from_slot(key: String) -> void:
	var it = _equipment.slots.get(key, {})
	if it == null or it.is_empty():
		return
	_return_item()
	_equipment.slots[key] = null
	_equipped = {"item": it, "source": "equip", "slot": key}
	_equipment.changed.emit()
	_refresh()

func _on_drop_equip(data: Dictionary) -> void:
	var slot := _find_bp_slot(data.get("item", {}))
	if slot < 0:
		show_message("请从背包拖入装备", true)
		return
	_equip_from_backpack(slot)

func _return_item() -> void:
	if _equipped.is_empty():
		return
	var item: Dictionary = _equipped["item"]
	var source := String(_equipped["source"])
	var slot = _equipped["slot"]
	if source == "equip" and _equipment.slots.get(slot, {}) == {}:
		_equipment.slots[slot] = item
		_equipment.changed.emit()
	else:
		_place_into_backpack(item)
	_equipped = {}
	_refresh()

func _place_into_backpack(item: Dictionary) -> void:
	for i in _backpack.slots.size():
		if _backpack.slots[i] == null:
			item["slot"] = i
			_backpack.slots[i] = item
			_backpack.changed.emit()
			return
	show_message("背包已满，物品无法归还", true)

func _enhance() -> void:
	if _equipped.is_empty():
		show_message("请先放入装备！", true)
		return
	var item: Dictionary = _equipped["item"]
	var level := int(item.get("enhanceLevel", 0))
	var max_level := NpcConfig.enhance_max_level(item)
	if level >= max_level:
		show_message("已达最高强化等级！", true)
		return
	var stone_slot := _find_material(NpcConfig.ENHANCE_STONE_ID)
	var wh_has: bool = _warehouse != null and _warehouse.count_material(_is_enhance_stone) > 0
	if stone_slot < 0 and not wh_has:
		show_message("强化石不足！需要 1 颗强化石", true)
		return
	var cost := NpcConfig.enhance_cost(level)
	if not economy.deduct_gold(cost):
		show_message("金币不足！需要 %d 金币" % cost, true)
		return
	if stone_slot >= 0:
		_consume_stack(stone_slot)
	else:
		_warehouse.consume_material(_is_enhance_stone, 1)
	item["enhanceLevel"] = level + 1
	show_message("强化成功！%s +%d" % [String(item.get("name", "?")), level + 1])
	_refresh()

func _is_enhance_stone(it) -> bool:
	return it != null and (String(it.get("id", "")) == NpcConfig.ENHANCE_STONE_ID or String(it.get("name", "")) == "强化石")

func _find_material(id: String) -> int:
	for i in _backpack.slots.size():
		var it = _backpack.slots[i]
		if it != null and String(it.get("id", "")) == id:
			return i
	for i in _backpack.slots.size():
		var it = _backpack.slots[i]
		if it != null and String(it.get("name", "")) == "强化石":
			return i
	return -1

func _consume_stack(slot: int) -> void:
	var it = _backpack.slots[slot]
	var stack := int(it.get("stack", 1))
	if stack <= 1:
		_backpack.slots[slot] = null
	else:
		it["stack"] = stack - 1
	_backpack.changed.emit()

func _predicted(item: Dictionary) -> String:
	var level := int(item.get("enhanceLevel", 0))
	var attrs := {}
	if _player_status != null:
		for k in ["str", "dex", "con", "wis", "luck"]:
			attrs[k] = int(_player_status.get(k))
		attrs["int"] = int(_player_status.get("intt"))
	if not WeaponFormula.get_attack_formula(item).is_empty():
		var cur := WeaponFormula.compute_weapon_atk(item, level, attrs)
		var nxt := WeaponFormula.compute_weapon_atk(item, level + 1, attrs)
		return "预测强化效果 (+%d)：物理攻击 %d → %d (+%d)\n公式：%s" % [
			level + 1, cur, nxt, nxt - cur, WeaponFormula.formula_text(item, level + 1)]
	var defense: Dictionary = item.get("defense", {})
	if not defense.is_empty():
		var dcur := float(defense.get("base", 0)) + float(defense.get("perEnhance", 0)) * level
		var dnxt := float(defense.get("base", 0)) + float(defense.get("perEnhance", 0)) * (level + 1)
		return "预测强化效果 (+%d)：物理防御 %.1f → %.1f (+%.1f)" % [level + 1, dcur, dnxt, dnxt - dcur]
	var stats: Array = item.get("stats", [])
	if not stats.is_empty() and typeof(stats[0]) == TYPE_DICTIONARY:
		return "强化后继续提升：%s %s" % [String(stats[0].get("name", "")), String(stats[0].get("value", ""))]
	return ""

func _on_changed() -> void:
	if _open:
		_refresh()
