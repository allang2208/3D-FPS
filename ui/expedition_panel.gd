extends "res://ui/npc_panel.gd"
## 出征准备面板（expedition-system.js 迁移）：10 格祭品栏（同名限 1 件），
## 当前地牢 僵尸地牢（F 级）需要「普通及以上」祭品；出征通过 depart_requested 交给 main。

const NpcConfig := preload("res://ui/npc_config.gd")

signal depart_requested(items: Array)

const CAPACITY := 10
const DUNGEON_GRADE := "F"

var _db: RefCounted
var _backpack: RefCounted
var _carried: Array = []

var _grid: GridContainer
var _bp_grid: GridContainer
var _capacity_label: Label
var _rule_label: Label
var _stats_label: Label

func setup(db: RefCounted, backpack: RefCounted, _equipment: RefCounted, _economy: RefCounted) -> void:
	_db = db
	_backpack = backpack
	_carried.resize(CAPACITY)
	for i in _carried.size():
		_carried[i] = null
	if _backpack != null and not _backpack.changed.is_connected(_on_changed):
		_backpack.changed.connect(_on_changed)

func _build_body() -> void:
	body.add_child(_make_section_title("⚔️ 出征条件"))
	var rule_text := (
		"F 级地牢 → 普通及以上祭品\n"
		+ "E 级地牢 → 优质及以上祭品\n"
		+ "D 级地牢 → 稀有及以上祭品\n"
		+ "C 级地牢 → 史诗及以上祭品\n"
		+ "B 级地牢 → 神话及以上祭品\n"
		+ "A 级地牢 → 传说及以上祭品"
	)
	body.add_child(_make_label(rule_text, "caption", Style.THEME_GRAY_LIGHT))
	_rule_label = _make_label("", "body", Style.THEME_GOLD)
	body.add_child(_rule_label)
	_capacity_label = _make_label("", "caption", Style.THEME_GRAY_LIGHT)
	body.add_child(_capacity_label)
	_stats_label = _make_label("", "body", Style.THEME_WHITE)
	body.add_child(_stats_label)

	body.add_child(_make_label("祭品栏（点击已放祭品取出）", "caption", Style.THEME_GRAY_LIGHT))
	var grid_scroll := ScrollContainer.new()
	grid_scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	grid_scroll.custom_minimum_size = Vector2(0, 170)
	body.add_child(grid_scroll)
	_grid = GridContainer.new()
	_grid.columns = 5
	_grid.add_theme_constant_override("h_separation", 6)
	_grid.add_theme_constant_override("v_separation", 6)
	grid_scroll.add_child(_grid)

	var actions := HBoxContainer.new()
	actions.add_theme_constant_override("separation", Style.spacing("element_gap"))
	body.add_child(actions)
	var depart_btn := _make_button("⚔️ 确认出征")
	depart_btn.pressed.connect(_depart)
	actions.add_child(depart_btn)
	var reset_btn := _make_button("↺ 重置")
	reset_btn.pressed.connect(_return_all)
	actions.add_child(reset_btn)

	body.add_child(_make_label("背包祭品", "caption", Style.THEME_GRAY_LIGHT))
	var bp_scroll := ScrollContainer.new()
	bp_scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	bp_scroll.custom_minimum_size = Vector2(0, 150)
	body.add_child(bp_scroll)
	_bp_grid = GridContainer.new()
	_bp_grid.columns = 5
	_bp_grid.add_theme_constant_override("h_separation", 6)
	_bp_grid.add_theme_constant_override("v_separation", 6)
	bp_scroll.add_child(_bp_grid)

func _refresh() -> void:
	_rule_label.text = "当前：僵尸地牢（%s 级） 需要「%s及以上」祭品" % [
		DUNGEON_GRADE, NpcConfig.rarity_label(_required_rarity())]
	var used := 0
	for c in _carried:
		if c != null:
			used += 1
	_capacity_label.text = "携带：%d / %d" % [used, CAPACITY]
	_rebuild_grid()
	_rebuild_backpack()
	_update_stats()

func _required_rarity() -> String:
	var idx := maxi(0, NpcConfig.RARITY_ORDER.find("common"))
	return String(NpcConfig.RARITY_ORDER[idx])

func _rebuild_grid() -> void:
	for c in _grid.get_children():
		c.queue_free()
	for i in _carried.size():
		var entry = _carried[i]
		if entry == null:
			var empty := _make_button("空", "body")
			empty.disabled = true
			_grid.add_child(empty)
			continue
		var item: Dictionary = entry["item"]
		var b := _make_item_cell(item, Vector2(120, 52))
		b.pressed.connect(func(_c, _idx: int = i): _remove_from_cell(_idx))
		_grid.add_child(b)

func _rebuild_backpack() -> void:
	for c in _bp_grid.get_children():
		c.queue_free()
	for i in _backpack.slots.size():
		var it = _backpack.slots[i]
		if it == null or it.is_empty() or String(it.get("category", "")) != "tribute":
			continue
		var b := _make_item_cell(it, Vector2(120, 52))
		b.pressed.connect(func(_c, _idx: int = i): _place_from_backpack(_idx))
		_bp_grid.add_child(b)

func _has_duplicate(item: Dictionary) -> bool:
	for c in _carried:
		if c != null and String(c["item"].get("name", "")) == String(item.get("name", "")):
			return true
	return false

func _place_from_backpack(bp_slot: int) -> void:
	var it = _backpack.slots[bp_slot]
	if it == null or it.is_empty() or String(it.get("category", "")) != "tribute":
		show_message("祭品栏只能放入祭品！", true)
		return
	if _has_duplicate(it):
		show_message("不可放入相同祭品！", true)
		return
	var slot := -1
	for i in _carried.size():
		if _carried[i] == null:
			slot = i
			break
	if slot < 0:
		show_message("携带空间已满！", true)
		return
	var stack := int(it.get("stack", 1))
	if stack <= 1:
		_backpack.slots[bp_slot] = null
	else:
		it["stack"] = stack - 1
	var clone: Dictionary = it.duplicate(true)
	clone["stack"] = 1
	_carried[slot] = {"item": clone, "count": 1}
	_backpack.changed.emit()
	_refresh()

func _remove_from_cell(slot: int) -> void:
	var entry = _carried[slot]
	if entry == null:
		return
	_carried[slot] = null
	_backpack.add_item(String(entry["item"].get("id", "")), 1)
	_refresh()

func _return_all() -> void:
	for i in _carried.size():
		var entry = _carried[i]
		if entry == null:
			continue
		_carried[i] = null
		_backpack.add_item(String(entry["item"].get("id", "")), 1)
	_refresh()

func _update_stats() -> void:
	var lines: Array = []
	for c in _carried:
		if c == null:
			continue
		var item: Dictionary = c["item"]
		for s in item.get("stats", []):
			lines.append("%s %s（%s）" % [String(s["name"]), String(s["value"]), String(item.get("name", ""))])
	_stats_label.text = "祭品效果：\n" + "\n".join(lines) if not lines.is_empty() else "祭品效果：无"

func _depart() -> void:
	var carried: Array = []
	for c in _carried:
		if c != null:
			carried.append(c)
	if carried.is_empty():
		show_message("请至少放入一种祭品", true)
		return
	var req_idx := NpcConfig.rarity_rank(_required_rarity())
	var ok := false
	for c in carried:
		if NpcConfig.rarity_rank(String(c["item"].get("rarity", "common"))) >= req_idx:
			ok = true
			break
	if not ok:
		show_message("请放入「%s及以上」祭品" % NpcConfig.rarity_label(_required_rarity()), true)
		return
	var items: Array = []
	for c in carried:
		items.append(c["item"])
	for i in _carried.size():
		_carried[i] = null
	depart_requested.emit(items)
	close()

func _on_changed() -> void:
	if _open:
		_refresh()
