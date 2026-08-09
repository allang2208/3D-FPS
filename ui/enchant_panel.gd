extends "res://ui/npc_panel.gd"
## 附魔面板（enchant-system.js 迁移）：卷轴 + 装备槽位，消耗魔法粉尘附魔；
## 卷轴可单独转换粉尘（奖励 = 消耗的一半）；兼容性按 weaponTypes 限制。

const NpcConfig := preload("res://ui/npc_config.gd")

var _db: RefCounted
var _equipment: RefCounted
var _warehouse: RefCounted
var _scroll := {}
var _equip := {}
var _equip_src := {}
var _scroll_src := {}

var _scroll_label: Label
var _equip_label: Label
var _dust_label: Label
var _preview_label: Label
var _scroll_grid: GridContainer
var _equip_grid: GridContainer
var _enchant_btn: Button

func setup(db: RefCounted, backpack: RefCounted, equipment: RefCounted, economy: RefCounted) -> void:
	_db = db
	_backpack = backpack
	_equipment = equipment
	set_economy(economy)
	if _backpack != null and not _backpack.changed.is_connected(_on_changed):
		_backpack.changed.connect(_on_changed)

func set_warehouse(wh: RefCounted) -> void:
	_warehouse = wh

func _build_body() -> void:
	body.add_child(_make_empty_hint("拖入卷轴点击转换粉尘可以生成粉尘，拖入装备和附魔卷轴进行附魔。"))
	var scroll_drop := _make_drop_slot()
	body.add_child(scroll_drop)
	_scroll_label = _make_label("卷轴槽：空", "body", Style.THEME_GRAY_LIGHT)
	_scroll_label.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	scroll_drop.add_child(_scroll_label)
	scroll_drop.dropped.connect(_on_drop_scroll)
	var equip_drop := _make_drop_slot()
	body.add_child(equip_drop)
	_equip_label = _make_label("装备槽：空", "body", Style.THEME_GRAY_LIGHT)
	_equip_label.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	equip_drop.add_child(_equip_label)
	equip_drop.dropped.connect(_on_drop_equip)
	_dust_label = _make_label("✨ 魔法粉尘：0", "body", Style.THEME_GOLD)
	body.add_child(_dust_label)
	body.add_child(_make_section_title("🔮 预览效果"))
	_preview_label = _make_label("", "body", Style.THEME_WHITE)
	body.add_child(_preview_label)

	var actions := HBoxContainer.new()
	actions.add_theme_constant_override("separation", Style.spacing("element_gap"))
	body.add_child(actions)
	_enchant_btn = _make_button("✨ 进行附魔")
	_enchant_btn.pressed.connect(_do_enchant)
	actions.add_child(_enchant_btn)
	var convert_btn := _make_button("💳 转换粉尘")
	convert_btn.pressed.connect(_convert_dust)
	actions.add_child(convert_btn)
	var reset_btn := _make_button("↺ 重置")
	reset_btn.pressed.connect(_reset)
	actions.add_child(reset_btn)

	var h := HBoxContainer.new()
	h.size_flags_vertical = Control.SIZE_EXPAND_FILL
	h.add_theme_constant_override("separation", Style.spacing("element_gap"))
	body.add_child(h)

	var sc_col := VBoxContainer.new()
	sc_col.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	sc_col.add_theme_constant_override("separation", Style.spacing("grid"))
	h.add_child(sc_col)
	sc_col.add_child(_make_section_title("📜 可用卷轴（双击/右键放入）"))
	var sc_scroll := ScrollContainer.new()
	sc_scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	sc_col.add_child(sc_scroll)
	_scroll_grid = GridContainer.new()
	_scroll_grid.columns = 1
	_scroll_grid.add_theme_constant_override("h_separation", 6)
	_scroll_grid.add_theme_constant_override("v_separation", 6)
	sc_scroll.add_child(_scroll_grid)

	var eq_col := VBoxContainer.new()
	eq_col.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	eq_col.add_theme_constant_override("separation", Style.spacing("grid"))
	h.add_child(eq_col)
	eq_col.add_child(_make_section_title("⚔️ 武器（背包 / 已装备）"))
	var eq_scroll := ScrollContainer.new()
	eq_scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	eq_col.add_child(eq_scroll)
	_equip_grid = GridContainer.new()
	_equip_grid.columns = 1
	_equip_grid.add_theme_constant_override("h_separation", 6)
	_equip_grid.add_theme_constant_override("v_separation", 6)
	eq_scroll.add_child(_equip_grid)

func _refresh() -> void:
	_refresh_gold()
	_dust_label.text = "✨ 魔法粉尘：%d" % _count_dust()
	_scroll_label.text = "卷轴槽：%s" % (String(_scroll.get("name", "空")) if not _scroll.is_empty() else "空")
	_equip_label.text = "装备槽：%s" % (String(_equip.get("name", "空")) if not _equip.is_empty() else "空")
	_update_preview()
	_rebuild_scroll_list()
	_rebuild_equip_list()

func _rebuild_scroll_list() -> void:
	for c in _scroll_grid.get_children():
		c.queue_free()
	for i in _backpack.slots.size():
		var it = _backpack.slots[i]
		if it == null or it.is_empty() or String(it.get("scroll_id", "")) == "":
			continue
		var cell := _make_item_cell(it, _cell_size("lg"))
		cell.pressed.connect(func(_c, _idx: int = i): _place_scroll("backpack", _idx))
		_scroll_grid.add_child(cell)
	if _warehouse != null:
		for it in _warehouse.items:
			if it == null or it.is_empty() or String(it.get("scroll_id", "")) == "":
				continue
			var cell := _make_item_cell(it, _cell_size("lg"))
			cell.pressed.connect(func(_c, _it: Dictionary = it): _place_scroll("warehouse", int(_it.get("slot", -1))))
			_scroll_grid.add_child(cell)

func _rebuild_equip_list() -> void:
	for c in _equip_grid.get_children():
		c.queue_free()
	for i in _backpack.slots.size():
		var it = _backpack.slots[i]
		if it == null or it.is_empty() or not _is_weapon(it):
			continue
		var cell := _make_item_cell(it, _cell_size("lg"))
		cell.pressed.connect(func(_c, _idx: int = i): _place_equip("backpack", _idx))
		_equip_grid.add_child(cell)
	for key in _equipment.SLOT_ORDER:
		var it = _equipment.slots.get(key, {})
		if it == null or it.is_empty() or not _is_weapon(it):
			continue
		var cell := _make_item_cell(it, _cell_size("lg"))
		cell.pressed.connect(func(_c, _key: String = String(key)): _place_equip("equip", _key))
		_equip_grid.add_child(cell)

func _is_weapon(item: Dictionary) -> bool:
	var cat := String(item.get("category", ""))
	return cat == "weapon_melee" or cat == "weapon_ranged"

func _place_scroll(source: String, slot: int) -> void:
	var it = _backpack.slots[slot] if source == "backpack" else _warehouse.get_item_at(slot)
	if it == null or it.is_empty() or String(it.get("scroll_id", "")) == "":
		return
	if not _equip.is_empty() and not NpcConfig.can_enchant(_equip, String(it.get("scroll_id", ""))):
		show_message("不符合附魔条件", true)
		return
	_return_scroll()
	if source == "backpack":
		_backpack.slots[slot] = null
	else:
		_warehouse.consume_material(func(i): return i == it, int(it.get("stack", 1)))
	_scroll = it
	_scroll_src = {"source": source, "slot": slot}
	_backpack.changed.emit()
	_refresh()

func _on_drop_scroll(data: Dictionary) -> void:
	var it: Dictionary = data.get("item", {})
	if String(it.get("scroll_id", "")) == "":
		show_message("请拖入附魔卷轴", true)
		return
	var slot := _find_bp_slot(it)
	if slot < 0:
		show_message("请从背包拖入卷轴", true)
		return
	_place_scroll("backpack", slot)

func _on_drop_equip(data: Dictionary) -> void:
	var it: Dictionary = data.get("item", {})
	if not _is_weapon(it):
		show_message("只能附魔武器", true)
		return
	var slot := _find_bp_slot(it)
	if slot < 0:
		show_message("请从背包拖入武器", true)
		return
	_place_equip("backpack", slot)

func _place_equip(source: String, slot) -> void:
	var it = _backpack.slots[slot] if source == "backpack" else _equipment.slots.get(slot, {})
	if it == null or it.is_empty() or not _is_weapon(it):
		return
	if not _scroll.is_empty() and not NpcConfig.can_enchant(it, String(_scroll.get("scroll_id", ""))):
		show_message("不符合附魔条件", true)
		_return_scroll()
		return
	_return_equip()
	if source == "backpack":
		_backpack.slots[slot] = null
	else:
		_equipment.slots[slot] = null
	_equip = it
	_equip_src = {"source": source, "slot": slot}
	_backpack.changed.emit()
	_refresh()

func _return_scroll() -> void:
	if _scroll.is_empty():
		return
	if not _scroll_src.is_empty() and String(_scroll_src.get("source", "")) == "warehouse" and _warehouse != null:
		if not _warehouse.add_item(_scroll):
			_place_into_backpack(_scroll)
	else:
		_place_into_backpack(_scroll)
	_scroll = {}
	_scroll_src = {}

func _return_equip() -> void:
	if _equip.is_empty():
		return
	var item: Dictionary = _equip
	if not _equip_src.is_empty() and String(_equip_src.get("source", "")) == "equip":
		var key := String(_equip_src["slot"])
		if _equipment.slots.get(key, {}) == {}:
			_equipment.slots[key] = item
			_equipment.changed.emit()
			_equip = {}
			_equip_src = {}
			return
	_place_into_backpack(item)
	_equip = {}
	_equip_src = {}

func _place_into_backpack(item: Dictionary) -> void:
	for i in _backpack.slots.size():
		if _backpack.slots[i] == null:
			item["slot"] = i
			_backpack.slots[i] = item
			_backpack.changed.emit()
			return
	show_message("背包已满，物品无法归还", true)

func _update_preview() -> void:
	if _scroll.is_empty() or _equip.is_empty():
		_preview_label.text = ""
		_enchant_btn.disabled = true
		return
	var scroll_id := String(_scroll.get("scroll_id", ""))
	if not NpcConfig.can_enchant(_equip, scroll_id):
		_preview_label.text = "不符合附魔条件"
		_enchant_btn.disabled = true
		return
	var scroll := NpcConfig.get_scroll(scroll_id)
	var preview := "%s %s" % [String(scroll.get("name", "?")), String(_equip.get("name", "?"))]
	if String(scroll.get("type", "")) == "suffix":
		preview = "%s %s" % [String(_equip.get("name", "?")), String(scroll.get("name", "?"))]
	preview += "\n%s\n消耗：✨ %d" % [String(scroll.get("desc", "")), int(scroll.get("cost", 0))]
	_preview_label.text = preview
	_enchant_btn.disabled = false

func _count_dust() -> int:
	var total := 0
	for i in _backpack.slots.size():
		var it = _backpack.slots[i]
		if it != null and (String(it.get("id", "")) == NpcConfig.MAGIC_DUST_ID or String(it.get("name", "")) == "魔法粉尘"):
			total += int(it.get("stack", 1))
	if _warehouse != null:
		total += _warehouse.count_material(_is_dust)
	return total

func _is_dust(it) -> bool:
	return it != null and (String(it.get("id", "")) == NpcConfig.MAGIC_DUST_ID or String(it.get("name", "")) == "魔法粉尘")

func _consume_dust(amount: int) -> void:
	var remaining := amount
	for i in range(_backpack.slots.size() - 1, -1, -1):
		var it = _backpack.slots[i]
		if it == null or (String(it.get("id", "")) != NpcConfig.MAGIC_DUST_ID and String(it.get("name", "")) != "魔法粉尘"):
			continue
		var stack := int(it.get("stack", 1))
		if stack <= remaining:
			remaining -= stack
			_backpack.slots[i] = null
		else:
			it["stack"] = stack - remaining
			remaining = 0
		if remaining <= 0:
			break
	if remaining > 0 and _warehouse != null:
		remaining -= _warehouse.consume_material(_is_dust, remaining)
	_backpack.changed.emit()

func _do_enchant() -> void:
	if _scroll.is_empty() or _equip.is_empty():
		show_message("请放入卷轴和装备", true)
		return
	var scroll_id := String(_scroll.get("scroll_id", ""))
	if not NpcConfig.can_enchant(_equip, scroll_id):
		show_message("不符合附魔条件", true)
		return
	var scroll := NpcConfig.get_scroll(scroll_id)
	var cost := int(scroll.get("cost", 0))
	if _count_dust() < cost:
		show_message("魔法粉尘不足（需要 %d，当前 %d）" % [cost, _count_dust()], true)
		return
	_consume_dust(cost)
	_scroll = {}  # 卷轴销毁
	var data: Dictionary = _equip.get("_enchantData", {})
	if String(scroll.get("type", "")) == "prefix":
		data["prefix"] = {"id": scroll_id, "name": String(scroll.get("name", "")), "grade": String(scroll.get("grade", ""))}
	else:
		data["suffix"] = {"id": scroll_id, "name": String(scroll.get("name", "")), "grade": String(scroll.get("grade", ""))}
	_equip["_enchantData"] = data
	_equip["_enchantEffects"] = scroll.get("effects", {}).duplicate(true)
	_equip["_isEnchanted"] = true
	show_message("附魔成功！")
	_refresh()

func _convert_dust() -> void:
	if _scroll.is_empty():
		show_message("请放入附魔卷轴", true)
		return
	var reward := NpcConfig.scroll_conversion_reward(String(_scroll.get("scroll_id", "")))
	if reward <= 0:
		show_message("该卷轴无法转换", true)
		return
	_scroll = {}
	_backpack.add_item(NpcConfig.MAGIC_DUST_ID, reward)
	show_message("转换获得 %d 魔法粉尘" % reward)
	_refresh()

func _reset() -> void:
	_return_scroll()
	_return_equip()
	_refresh()

func _on_changed() -> void:
	if _open:
		_refresh()
