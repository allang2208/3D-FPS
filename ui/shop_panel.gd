extends "res://ui/npc_panel.gd"
## 商店面板（shop-system.js 迁移）：左侧购买目录，右侧出售栏。
## 购买价 = 商店价（shopPrice 缺省 price，price 缺省按稀有度标准价）；出售价 = max(1, price*0.5)。

const NpcConfig := preload("res://ui/npc_config.gd")

var _db: RefCounted
var _shop_id := "main"
var _sell: Array = []  # Array[{item, slot}]

var _buy_grid: GridContainer
var _sell_grid: GridContainer
var _bp_grid: GridContainer
var _sell_empty: Label

func setup(db: RefCounted, backpack: RefCounted, _equipment: RefCounted, economy: RefCounted) -> void:
	_db = db
	_backpack = backpack
	set_economy(economy)
	if _backpack != null and not _backpack.changed.is_connected(_on_backpack_changed):
		_backpack.changed.connect(_on_backpack_changed)

func set_shop_id(v: String) -> void:
	_shop_id = v

func _build_body() -> void:
	var h := HBoxContainer.new()
	h.add_theme_constant_override("separation", Style.spacing("element_gap"))
	body.add_child(h)

	var buy_col := VBoxContainer.new()
	buy_col.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	buy_col.add_theme_constant_override("separation", Style.spacing("grid"))
	h.add_child(buy_col)
	buy_col.add_child(_make_section_title("📦 商品购买"))
	var buy_scroll := ScrollContainer.new()
	buy_scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	buy_scroll.custom_minimum_size = Vector2(400, 320)
	buy_col.add_child(buy_scroll)
	_buy_grid = GridContainer.new()
	_buy_grid.columns = 3
	_buy_grid.add_theme_constant_override("h_separation", 6)
	_buy_grid.add_theme_constant_override("v_separation", 6)
	buy_scroll.add_child(_buy_grid)

	var sell_col := VBoxContainer.new()
	sell_col.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	sell_col.add_theme_constant_override("separation", Style.spacing("grid"))
	h.add_child(sell_col)
	sell_col.add_child(_make_section_title("🛒 我的卖出"))
	var sell_scroll := ScrollContainer.new()
	sell_scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	sell_scroll.custom_minimum_size = Vector2(360, 160)
	sell_col.add_child(sell_scroll)
	_sell_grid = GridContainer.new()
	_sell_grid.columns = 3
	_sell_grid.add_theme_constant_override("h_separation", 6)
	_sell_grid.add_theme_constant_override("v_separation", 6)
	sell_scroll.add_child(_sell_grid)

	_sell_empty = _make_empty_hint("双击或右键点击背包/装备栏物品，或拖动至此")
	sell_col.add_child(_sell_empty)

	sell_col.add_child(_make_section_title("🎒 背包"))
	var bp_scroll := ScrollContainer.new()
	bp_scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	bp_scroll.custom_minimum_size = Vector2(360, 160)
	sell_col.add_child(bp_scroll)
	_bp_grid = GridContainer.new()
	_bp_grid.columns = 3
	_bp_grid.add_theme_constant_override("h_separation", 6)
	_bp_grid.add_theme_constant_override("v_separation", 6)
	bp_scroll.add_child(_bp_grid)

	var sell_btn := _make_button("💰 确认卖出")
	sell_btn.pressed.connect(_confirm_sell)
	sell_col.add_child(sell_btn)

func _refresh() -> void:
	var hud := get_node_or_null("/root/HUD")
	if hud != null:
		hud.request_inventory_save()
	_refresh_gold()
	_rebuild_buy_grid()
	_rebuild_sell_grid()
	_rebuild_backpack_grid()

func _catalog_items() -> Array:
	var ids: Array = NpcConfig.SHOP_CATALOGS.get(_shop_id, NpcConfig.SHOP_CATALOGS["main"])
	var out: Array = []
	for id in ids:
		var def: Dictionary = _db.get_def(String(id))
		if def.is_empty():
			continue
		var it: Dictionary = def.duplicate(true)
		it["id"] = String(id)
		it["price"] = NpcConfig.standard_price(def)
		out.append(it)
	return out

func _rebuild_buy_grid() -> void:
	for c in _buy_grid.get_children():
		c.queue_free()
	for item in _catalog_items():
		var cell := _make_item_cell(item)
		cell.set_price(int(item["price"]))
		var id := String(item["id"])
		var price := int(item["price"])
		cell.pressed.connect(func(_c): _buy(id, price))
		_buy_grid.add_child(cell)

func _rebuild_sell_grid() -> void:
	for c in _sell_grid.get_children():
		c.queue_free()
	_sell_empty.visible = _sell.is_empty()
	for i in _sell.size():
		var it: Dictionary = _sell[i]["item"]
		var sell_price := maxi(1, int(NpcConfig.standard_price(it) * 0.5))
		var cell := _make_item_cell(it, _cell_size("sm"))
		cell.set_price(sell_price)
		cell.pressed.connect(func(_c, _idx: int = i): _return_to_backpack(_idx))
		cell.drop_requested.connect(func(d):
			var s := _find_bp_slot(d.get("item", {}))
			if s >= 0:
				_add_to_sell(s))
		_sell_grid.add_child(cell)

func _rebuild_backpack_grid() -> void:
	for c in _bp_grid.get_children():
		c.queue_free()
	for i in _backpack.slots.size():
		var it = _backpack.slots[i]
		if it == null or it.is_empty():
			continue
		var cell := _make_item_cell(it, _cell_size("sm"))
		cell.pressed.connect(func(_c, _idx: int = i): _add_to_sell(_idx))
		_bp_grid.add_child(cell)

func _buy(id: String, cost: int) -> void:
	if not _backpack.can_add(_db.create_instance(id, 1)):
		show_message("背包已满！", true)
		return
	if not economy.deduct_gold(cost):
		show_message("金币不足！需要 %d 金币" % cost, true)
		return
	if not _backpack.add_item(id, 1):
		economy.add_gold(cost)
		show_message("购买失败", true)
		return
	show_message("购买成功：%s" % String(_db.get_def(id).get("name", id)))
	_refresh()

func _add_to_sell(slot: int) -> void:
	var it = _backpack.slots[slot]
	if it == null or it.is_empty():
		return
	if String(it.get("category", "")) == "gold" or String(it.get("name", "")) == "金币":
		show_message("金币不可卖出", true)
		return
	_sell.append({"item": it.duplicate(true), "slot": slot})
	_backpack.slots[slot] = null
	_backpack.changed.emit()
	_refresh()

func _return_to_backpack(index: int) -> void:
	if index < 0 or index >= _sell.size():
		return
	var entry: Dictionary = _sell[index]
	if not _backpack.add_instance(entry["item"], int(entry.get("slot", -1))):
		show_message("背包已满", true)
		return
	_sell.remove_at(index)
	_refresh()

func _confirm_sell() -> void:
	if _sell.is_empty():
		show_message("出售栏为空！", true)
		return
	var total := 0
	for entry in _sell:
		var price := maxi(1, int(NpcConfig.standard_price(entry["item"]) * 0.5))
		total += price * int(entry["item"].get("stack", 1))
	economy.add_gold(total)
	show_message("卖出 %d 件物品，获得 %d 金币" % [_sell.size(), total])
	_sell.clear()
	_refresh()

func _on_backpack_changed() -> void:
	if _open:
		_refresh()
