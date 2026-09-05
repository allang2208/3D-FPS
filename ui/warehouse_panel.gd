extends "res://ui/npc_panel.gd"
## 仓库面板（warehouse-system.js 迁移，精简版）：分页格子 + 存入/取出。
## 当前未接入 NPC 对话选项（旧版仓库 NPC 直接开面板），数据层已供强化/改造/附魔扣减。

var _db: RefCounted
var _warehouse: RefCounted

var _grid: GridContainer
var _page_label: Label

func setup(db: RefCounted, backpack: RefCounted, _equipment: RefCounted, _economy: RefCounted) -> void:
	_db = db
	_backpack = backpack

func set_warehouse(wh: RefCounted) -> void:
	_warehouse = wh
	if _warehouse != null and not _warehouse.changed.is_connected(_on_changed):
		_warehouse.changed.connect(_on_changed)

func _build_body() -> void:
	body.add_child(_make_label("仓库（双击/点击取出，背包物品点击存入）", "caption", Color.WHITE))
	var scroll := ScrollContainer.new()
	scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	scroll.custom_minimum_size = Vector2(0, 260)
	body.add_child(scroll)
	_grid = GridContainer.new()
	_grid.columns = 5
	_grid.add_theme_constant_override("h_separation", 6)
	_grid.add_theme_constant_override("v_separation", 6)
	scroll.add_child(_grid)

	var actions := HBoxContainer.new()
	actions.add_theme_constant_override("separation", Style.spacing("element_gap"))
	body.add_child(actions)
	var store_btn := _make_button("全部存入")
	store_btn.pressed.connect(_store_all)
	actions.add_child(store_btn)
	var sort_btn := _make_button("整理")
	sort_btn.pressed.connect(func(): _warehouse.sort_items())
	actions.add_child(sort_btn)
	var take_btn := _make_button("全部取出")
	take_btn.pressed.connect(_take_all)
	actions.add_child(take_btn)
	var prev_btn := _make_button("◀ 上一页")
	prev_btn.pressed.connect(_page.bind(-1))
	actions.add_child(prev_btn)
	var next_btn := _make_button("下一页 ▶")
	next_btn.pressed.connect(_page.bind(1))
	actions.add_child(next_btn)
	_page_label = _make_label("", "caption", Color.WHITE)
	_page_label.autowrap_mode = TextServer.AUTOWRAP_OFF
	_page_label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	actions.add_child(_page_label)

	var bp_scroll := ScrollContainer.new()
	bp_scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	bp_scroll.custom_minimum_size = Vector2(0, 120)
	body.add_child(bp_scroll)
	_bp_grid = GridContainer.new()
	_bp_grid.columns = 5
	_bp_grid.add_theme_constant_override("h_separation", 6)
	_bp_grid.add_theme_constant_override("v_separation", 6)
	bp_scroll.add_child(_bp_grid)

var _bp_grid: GridContainer

func _refresh() -> void:
	if _warehouse == null:
		return
	_page_label.text = "第 %d/%d 页  %d/%d" % [
		_warehouse.current_page + 1, _warehouse.PAGE_COUNT,
		_warehouse.items.size(), _warehouse.CAPACITY]
	_rebuild_grid()
	_rebuild_backpack()

func _rebuild_grid() -> void:
	for c in _grid.get_children():
		c.queue_free()
	var start: int = _warehouse.current_page * _warehouse.PAGE_SIZE
	for i in _warehouse.PAGE_SIZE:
		var slot: int = start + int(i)
		var item: Dictionary = _warehouse.get_item_at(slot)
		var cell := _make_item_cell(item, _cell_size("std"))
		cell.set_meta("inventory_source", "warehouse")
		cell.set_meta("inventory_slot", slot)
		cell.pressed.connect(func(_c): _take_item(slot))
		cell.drop_requested.connect(func(data): _drop_to_warehouse(data, slot))
		_grid.add_child(cell)

func _drop_to_warehouse(data: Dictionary, target: int) -> void:
	if data.get("source", "") == "warehouse":
		_warehouse.move_item(int(data.get("slot", -1)), target)
	else:
		var source := _find_bp_slot(data.get("item", {}))
		if source >= 0:
			_warehouse.store_from_backpack(_backpack, source, target)
	_refresh()

func _rebuild_backpack() -> void:
	for c in _bp_grid.get_children():
		c.queue_free()
	for i in _backpack.slots.size():
		var value = _backpack.slots[i]
		var item: Dictionary = value if value != null else {}
		var cell := _make_item_cell(item, _cell_size("std"))
		cell.set_meta("inventory_source", "backpack")
		cell.set_meta("inventory_slot", i)
		cell.pressed.connect(func(_c): _store_item(i))
		cell.drop_requested.connect(func(data):
			if data.get("source", "") == "warehouse":
				_warehouse.retrieve_to_backpack(_backpack, int(data.get("slot", -1)), i)
			else:
				_backpack.swap_items(_find_bp_slot(data.get("item", {})), i)
			_refresh())
		_bp_grid.add_child(cell)

func _store_item(bp_slot: int) -> void:
	if not _warehouse.store_from_backpack(_backpack, bp_slot):
		show_message("仓库已满", true)
	_refresh()

func _take_item(w_slot: int) -> void:
	if not _warehouse.retrieve_to_backpack(_backpack, w_slot):
		show_message("背包已满", true)
	_refresh()

func _store_all() -> void:
	for i in _backpack.slots.size():
		if _backpack.slots[i] != null and not _warehouse.store_from_backpack(_backpack, i):
			show_message("仓库已满", true)
			break
	_refresh()

func _take_all() -> void:
	if _warehouse != null:
		_warehouse.retrieve_all_to_backpack(_backpack)
	_refresh()

func _page(delta: int) -> void:
	if _warehouse == null:
		return
	_warehouse.current_page = clampi(_warehouse.current_page + delta, 0, _warehouse.PAGE_COUNT - 1)
	_refresh()

func _on_changed() -> void:
	if _open:
		_refresh()
