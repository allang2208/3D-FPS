extends "res://ui/npc_panel.gd"
## 改造面板（craft-system.js 迁移）：放入可改造武器 -> 点击 mod 槽选择配件。
## 消耗改造券：首次 1 张，替换已改造配件 4 张；效果按 effects 聚合存入 item._craftEffects。
## 说明：旧版拖拽布局编辑（craft-config.json 坐标）未迁移，仅保留 mod 选择逻辑。

const NpcConfig := preload("res://ui/npc_config.gd")

var _db: RefCounted
var _backpack: RefCounted
var _equipment: RefCounted
var _warehouse: RefCounted
var _equipped := {}
var _popup_slot_id := ""

var _slot_label: Label
var _mod_grid: GridContainer
var _mod_title: Label
var _popup: PanelContainer
var _popup_list: VBoxContainer
var _bp_grid: GridContainer
var _eq_grid: GridContainer

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
	_slot_label = _make_label("改造槽：空（点击下方武器放入）", "body", Style.THEME_GRAY_LIGHT)
	body.add_child(_slot_label)
	_mod_title = _make_label("", "label", Style.THEME_GOLD)
	body.add_child(_mod_title)

	var h := HBoxContainer.new()
	h.size_flags_vertical = Control.SIZE_EXPAND_FILL
	h.add_theme_constant_override("separation", Style.spacing("element_gap"))
	body.add_child(h)

	var left := VBoxContainer.new()
	left.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	left.add_theme_constant_override("separation", Style.spacing("grid"))
	h.add_child(left)
	var mod_scroll := ScrollContainer.new()
	mod_scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	mod_scroll.custom_minimum_size = Vector2(300, 240)
	left.add_child(mod_scroll)
	_mod_grid = GridContainer.new()
	_mod_grid.columns = 2
	_mod_grid.add_theme_constant_override("h_separation", 6)
	_mod_grid.add_theme_constant_override("v_separation", 6)
	mod_scroll.add_child(_mod_grid)

	var actions := HBoxContainer.new()
	actions.add_theme_constant_override("separation", Style.spacing("element_gap"))
	left.add_child(actions)
	var remove_btn := _make_button("取下武器")
	remove_btn.pressed.connect(_return_item)
	actions.add_child(remove_btn)

	_popup = PanelContainer.new()
	_popup.name = "ModPopup"
	_popup.visible = false
	_popup.add_theme_stylebox_override("panel", Style.make_style(
		Style.THEME_BG, Style.THEME_GOLD, Style.RADIUS_MD, 1))
	_popup.custom_minimum_size = Vector2(430, 0)
	left.add_child(_popup)
	_popup_list = VBoxContainer.new()
	_popup_list.add_theme_constant_override("separation", Style.spacing("grid"))
	_popup.add_child(_popup_list)

	var bp_col := VBoxContainer.new()
	bp_col.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	bp_col.add_theme_constant_override("separation", Style.spacing("grid"))
	h.add_child(bp_col)
	bp_col.add_child(_make_label("背包", "caption", Style.THEME_GRAY_LIGHT))
	var bp_scroll := ScrollContainer.new()
	bp_scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	bp_col.add_child(bp_scroll)
	_bp_grid = GridContainer.new()
	_bp_grid.columns = 2
	_bp_grid.add_theme_constant_override("h_separation", 6)
	_bp_grid.add_theme_constant_override("v_separation", 6)
	bp_scroll.add_child(_bp_grid)

	var eq_col := VBoxContainer.new()
	eq_col.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	eq_col.add_theme_constant_override("separation", Style.spacing("grid"))
	h.add_child(eq_col)
	eq_col.add_child(_make_label("已装备（可放入改造）", "caption", Style.THEME_GRAY_LIGHT))
	var eq_scroll := ScrollContainer.new()
	eq_scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	eq_col.add_child(eq_scroll)
	_eq_grid = GridContainer.new()
	_eq_grid.columns = 2
	_eq_grid.add_theme_constant_override("h_separation", 6)
	_eq_grid.add_theme_constant_override("v_separation", 6)
	eq_scroll.add_child(_eq_grid)

func _refresh() -> void:
	_refresh_gold()
	_popup.visible = false
	if _equipped.is_empty():
		_slot_label.text = "改造槽：空（点击下方武器放入）"
		_mod_title.text = ""
	else:
		var item: Dictionary = _equipped["item"]
		_slot_label.text = "改造槽：%s%s" % [String(item.get("name", "?")), "（已改造）" if _is_crafted(item) else ""]
		_mod_title.text = "改造配件（点击格子选择）：" if NpcConfig.has_craft_config(item) else "该武器不可改造"
	_rebuild_mod_grid()
	_rebuild_backpack()

func _is_crafted(item: Dictionary) -> bool:
	var data: Dictionary = item.get("_craftData", {})
	return not data.is_empty()

func _rebuild_mod_grid() -> void:
	for c in _mod_grid.get_children():
		c.queue_free()
	if _equipped.is_empty():
		return
	var item: Dictionary = _equipped["item"]
	var cfg := NpcConfig.craft_config_for(item)
	if cfg.is_empty():
		return
	var mods: Dictionary = item.get("_craftData", {})
	for slot in cfg["slots"]:
		var slot_id := String(slot["id"])
		var slot_name := String(slot["name"])
		var current := String(mods.get(slot_id, ""))
		var label := slot_name
		if current != "":
			var opt := _find_option(cfg, slot_id, current)
			label = "%s：%s" % [slot_name, String(opt.get("name", current))]
		var b := _make_button(label, "body")
		if current != "":
			b.add_theme_color_override("font_color", Style.THEME_GOLD)
		b.pressed.connect(_open_popup.bind(String(slot_id)))
		_mod_grid.add_child(b)

func _find_option(cfg: Dictionary, slot_id: String, mod_id: String) -> Dictionary:
	var opts: Array = cfg.get("options", {}).get(slot_id, [])
	for o in opts:
		if String(o.get("id", "")) == mod_id:
			return o
	return {}

func _rebuild_backpack() -> void:
	for c in _bp_grid.get_children():
		c.queue_free()
	for i in _backpack.slots.size():
		var it = _backpack.slots[i]
		if it == null or it.is_empty():
			continue
		var b := _make_item_button(it, Vector2(170, 44))
		b.pressed.connect(_equip_from_backpack.bind(i))
		_bp_grid.add_child(b)
	for c in _eq_grid.get_children():
		c.queue_free()
	for key in _equipment.SLOT_ORDER:
		var it = _equipment.slots.get(key, {})
		if it == null or it.is_empty():
			continue
		var b := _make_item_button(it, Vector2(170, 44))
		b.pressed.connect(_equip_from_slot.bind(String(key)))
		_eq_grid.add_child(b)

func _equip_from_backpack(slot: int) -> void:
	var it = _backpack.slots[slot]
	if it == null or it.is_empty() or not NpcConfig.is_craftable(it):
		show_message("只能放入可改造的武器", true)
		return
	_return_item()
	_backpack.slots[slot] = null
	_equipped = {"item": it, "source": "backpack", "slot": slot}
	_backpack.changed.emit()
	_refresh()

func _equip_from_slot(key: String) -> void:
	var it = _equipment.slots.get(key, {})
	if it == null or it.is_empty() or not NpcConfig.is_craftable(it):
		show_message("只能放入可改造的武器", true)
		return
	_return_item()
	_equipment.slots[key] = null
	_equipped = {"item": it, "source": "equip", "slot": key}
	_equipment.changed.emit()
	_refresh()

func _return_item() -> void:
	if _equipped.is_empty():
		return
	var item: Dictionary = _equipped["item"]
	var source := String(_equipped.get("source", "backpack"))
	if source == "equip":
		var key := String(_equipped["slot"])
		if _equipment.slots.get(key, {}) == {}:
			_equipment.slots[key] = item
			_equipment.changed.emit()
			_equipped = {}
			_refresh()
			return
	var slot: int = _equipped["slot"]
	if source != "equip" and slot >= 0 and slot < _backpack.slots.size() and _backpack.slots[slot] == null:
		item["slot"] = slot
		_backpack.slots[slot] = item
	else:
		var empty := -1
		for i in _backpack.slots.size():
			if _backpack.slots[i] == null:
				empty = i
				break
		if empty < 0:
			show_message("背包已满，武器无法归还", true)
			return
		item["slot"] = empty
		_backpack.slots[empty] = item
	_backpack.changed.emit()
	_equipped = {}
	_refresh()

func _open_popup(slot_id: String) -> void:
	if _equipped.is_empty():
		return
	var cfg := NpcConfig.craft_config_for(_equipped["item"])
	if cfg.is_empty():
		return
	_popup_slot_id = slot_id
	for c in _popup_list.get_children():
		c.queue_free()
	var mods: Dictionary = _equipped["item"].get("_craftData", {})
	var current := String(mods.get(slot_id, ""))
	var opts: Array = cfg.get("options", {}).get(slot_id, [])
	for opt in opts:
		var mod_id := String(opt["id"])
		var label := "%s ｜ %s" % [String(opt["name"]), String(opt["desc"])]
		if mod_id == current:
			label = "✓ " + label
		var b := _make_button(label, "body")
		b.custom_minimum_size = Vector2(400, 0)
		b.pressed.connect(_equip_mod.bind(slot_id, mod_id))
		_popup_list.add_child(b)
	var cancel := _make_button("取消", "body")
	cancel.pressed.connect(func() -> void: _popup.visible = false)
	_popup_list.add_child(cancel)
	_popup.visible = true

func _equip_mod(slot_id: String, mod_id: String) -> void:
	_popup.visible = false
	if _equipped.is_empty():
		return
	var item: Dictionary = _equipped["item"]
	var mods: Dictionary = item.get("_craftData", {})
	if String(mods.get(slot_id, "")) == mod_id:
		return
	var has_existing := mods.has(slot_id)
	var cost := 4 if has_existing else 1
	var ticket_slot := _find_ticket()
	var bp_stack := int(_backpack.slots[ticket_slot].get("stack", 1)) if ticket_slot >= 0 else 0
	var wh_stack: int = _warehouse.count_material(_is_ticket) if _warehouse != null else 0
	if bp_stack + wh_stack < cost:
		show_message("改造券不足！需要 %d 张改造券%s" % [cost, "（替换已改造配件）" if has_existing else ""], true)
		return
	if bp_stack >= cost:
		_consume_tickets(ticket_slot, cost)
	else:
		if ticket_slot >= 0:
			_consume_tickets(ticket_slot, bp_stack)
		_warehouse.consume_material(_is_ticket, cost - bp_stack)
	mods[slot_id] = mod_id
	item["_craftData"] = mods
	item["_isCrafted"] = true
	item["_craftEffects"] = _aggregate_effects(item)
	show_message("改造成功！消耗 改造券×%d" % cost)
	_refresh()

func _aggregate_effects(item: Dictionary) -> Dictionary:
	var cfg := NpcConfig.craft_config_for(item)
	var mods: Dictionary = item.get("_craftData", {})
	var out := {}
	for slot_id in mods:
		var opt := _find_option(cfg, String(slot_id), String(mods[slot_id]))
		var effects: Dictionary = opt.get("effects", {})
		for key in effects:
			if out.has(key) and typeof(out[key]) == TYPE_FLOAT and typeof(effects[key]) == TYPE_FLOAT:
				out[key] = float(out[key]) + float(effects[key])
			elif out.has(key) and typeof(out[key]) == TYPE_INT and typeof(effects[key]) == TYPE_INT:
				out[key] = int(out[key]) + int(effects[key])
			else:
				out[key] = effects[key]
	return out

func _find_ticket() -> int:
	for i in _backpack.slots.size():
		var it = _backpack.slots[i]
		if it != null and String(it.get("id", "")) == NpcConfig.REFORGE_TICKET_ID:
			return i
	for i in _backpack.slots.size():
		var it = _backpack.slots[i]
		if it != null and String(it.get("name", "")) == "改造券":
			return i
	return -1

func _is_ticket(it) -> bool:
	return it != null and (String(it.get("id", "")) == NpcConfig.REFORGE_TICKET_ID or String(it.get("name", "")) == "改造券")

func _consume_tickets(slot: int, count: int) -> void:
	var it = _backpack.slots[slot]
	var stack := int(it.get("stack", 1))
	if stack <= count:
		_backpack.slots[slot] = null
	else:
		it["stack"] = stack - count
	_backpack.changed.emit()

func _on_changed() -> void:
	if _open:
		_refresh()
