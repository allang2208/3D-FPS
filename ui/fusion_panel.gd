extends "res://ui/npc_panel.gd"
## 祭品合成面板（fusion-system.js 迁移）：同稀有度祭品两两熔铸为更高一级；
## 传说对 -> 随机新传说；奇数保留最后放入的一件；只接受 tribute 类。

const NpcConfig := preload("res://ui/npc_config.gd")

var _db: RefCounted
var _backpack: RefCounted
var _placed: Array = []
var _seq := 0

var _grid: GridContainer
var _bp_grid: GridContainer
var _rarity_menu_btn: Button
var _rarity_menu: VBoxContainer

func setup(db: RefCounted, backpack: RefCounted, _equipment: RefCounted, _economy: RefCounted) -> void:
	_db = db
	_backpack = backpack
	_placed.resize(NpcConfig.FUSION_CAPACITY)
	for i in _placed.size():
		_placed[i] = null
	if _backpack != null and not _backpack.changed.is_connected(_on_changed):
		_backpack.changed.connect(_on_changed)

func _build_body() -> void:
	body.add_child(_make_label("祭品合成槽（双击放入/点击取出；至少 2 个同稀有度祭品）", "caption", Style.THEME_GRAY_LIGHT))
	var grid_scroll := ScrollContainer.new()
	grid_scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	grid_scroll.custom_minimum_size = Vector2(0, 220)
	body.add_child(grid_scroll)
	_grid = GridContainer.new()
	_grid.columns = 5
	_grid.add_theme_constant_override("h_separation", 6)
	_grid.add_theme_constant_override("v_separation", 6)
	grid_scroll.add_child(_grid)

	var actions := HBoxContainer.new()
	actions.add_theme_constant_override("separation", Style.spacing("element_gap"))
	body.add_child(actions)
	var fuse_btn := _make_button("🔮 合成")
	fuse_btn.pressed.connect(_fuse)
	actions.add_child(fuse_btn)
	var reset_btn := _make_button("↺ 重置")
	reset_btn.pressed.connect(_return_all)
	actions.add_child(reset_btn)
	_rarity_menu_btn = _make_button("⬇ 一键放入（按稀有度）")
	_rarity_menu_btn.pressed.connect(_toggle_rarity_menu)
	actions.add_child(_rarity_menu_btn)

	_rarity_menu = VBoxContainer.new()
	_rarity_menu.visible = false
	_rarity_menu.add_theme_constant_override("separation", Style.spacing("grid"))
	body.add_child(_rarity_menu)

	body.add_child(_make_label("背包祭品", "caption", Style.THEME_GRAY_LIGHT))
	var bp_scroll := ScrollContainer.new()
	bp_scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	bp_scroll.custom_minimum_size = Vector2(0, 160)
	body.add_child(bp_scroll)
	_bp_grid = GridContainer.new()
	_bp_grid.columns = 5
	_bp_grid.add_theme_constant_override("h_separation", 6)
	_bp_grid.add_theme_constant_override("v_separation", 6)
	bp_scroll.add_child(_bp_grid)

func _refresh() -> void:
	_rebuild_grid()
	_rebuild_backpack()
	_rarity_menu.visible = false

func _rebuild_grid() -> void:
	for c in _grid.get_children():
		c.queue_free()
	for i in _placed.size():
		var entry = _placed[i]
		if entry == null:
			var empty := _make_button("空", "body")
			empty.disabled = true
			_grid.add_child(empty)
			continue
		var item: Dictionary = entry["item"]
		var b := _make_item_button(item, Vector2(120, 44))
		b.text += " [%s]" % NpcConfig.rarity_label(String(item.get("rarity", "common")))
		b.pressed.connect(_retrieve.bind(i))
		_grid.add_child(b)

func _rebuild_backpack() -> void:
	for c in _bp_grid.get_children():
		c.queue_free()
	for i in _backpack.slots.size():
		var it = _backpack.slots[i]
		if it == null or it.is_empty() or String(it.get("category", "")) != "tribute":
			continue
		var b := _make_item_button(it, Vector2(120, 44))
		b.pressed.connect(_place_from_backpack.bind(i))
		_bp_grid.add_child(b)

func _free_slot() -> int:
	for i in _placed.size():
		if _placed[i] == null:
			return i
	return -1

func _place_from_backpack(bp_slot: int) -> void:
	var it = _backpack.slots[bp_slot]
	if it == null or it.is_empty() or String(it.get("category", "")) != "tribute":
		show_message("只能放入祭品", true)
		return
	var slot := _free_slot()
	if slot < 0:
		show_message("合成栏已满", true)
		return
	var stack := int(it.get("stack", 1))
	if stack <= 1:
		_backpack.slots[bp_slot] = null
	else:
		it["stack"] = stack - 1
	var clone: Dictionary = it.duplicate(true)
	clone["stack"] = 1
	_placed[slot] = {"item": clone, "seq": _seq}
	_seq += 1
	_backpack.changed.emit()
	_refresh()

func _retrieve(slot: int) -> void:
	var entry = _placed[slot]
	if entry == null:
		return
	_placed[slot] = null
	_backpack.add_item(String(entry["item"].get("id", "")), 1)
	_refresh()

func _return_all() -> void:
	for i in _placed.size():
		var entry = _placed[i]
		if entry == null:
			continue
		_placed[i] = null
		_backpack.add_item(String(entry["item"].get("id", "")), 1)
	_refresh()

func _fuse() -> void:
	var placed: Array = []
	for entry in _placed:
		if entry != null:
			placed.append(entry)
	if placed.size() < 2:
		show_message("至少放入 2 个祭品", true)
		return
	var rarity := String(placed[0]["item"].get("rarity", "common"))
	for entry in placed:
		if String(entry["item"].get("rarity", "common")) != rarity:
			show_message("请放入相同稀有度的祭品", true)
			return
	placed.sort_custom(func(a, b) -> bool: return int(a["seq"]) < int(b["seq"]))
	var results: Array = []
	for i in range(0, placed.size() - 1, 2):
		var next := _next_tribute(rarity)
		if not next.is_empty():
			results.append(next)
	var remainder: Array = []
	if placed.size() % 2 == 1:
		remainder.append(placed[placed.size() - 1]["item"])
	for i in _placed.size():
		_placed[i] = null
	for item in results + remainder:
		var slot := _free_slot()
		if slot < 0:
			break
		_placed[slot] = {"item": item, "seq": _seq}
		_seq += 1
	_refresh()
	if not results.is_empty():
		show_message("合成成功：%s" % "、".join(results.map(func(i): return String(i.get("name", "?")))))

func _next_tribute(rarity: String) -> Dictionary:
	var idx := NpcConfig.rarity_rank(rarity)
	var next_rarity := rarity
	if idx >= 0 and idx < NpcConfig.RARITY_ORDER.size() - 1:
		next_rarity = String(NpcConfig.RARITY_ORDER[idx + 1])
	var id := "tribute_%s" % next_rarity
	return _db.create_instance(id, 1)

func _toggle_rarity_menu() -> void:
	for c in _rarity_menu.get_children():
		c.queue_free()
	if _rarity_menu.visible:
		_rarity_menu.visible = false
		return
	var present := {}
	for i in _backpack.slots.size():
		var it = _backpack.slots[i]
		if it != null and String(it.get("category", "")) == "tribute":
			present[String(it.get("rarity", "common"))] = true
	for rarity in NpcConfig.RARITY_ORDER:
		if not present.has(rarity):
			continue
		var b := _make_button("放入全部 %s 祭品" % NpcConfig.rarity_label(rarity), "body")
		b.pressed.connect(_store_all_by_rarity.bind(rarity))
		_rarity_menu.add_child(b)
	_rarity_menu.visible = true

func _store_all_by_rarity(rarity: String) -> void:
	for i in _backpack.slots.size():
		var it = _backpack.slots[i]
		if it == null or it.is_empty() or String(it.get("category", "")) != "tribute" or String(it.get("rarity", "common")) != rarity:
			continue
		var stack := int(it.get("stack", 1))
		for _k in stack:
			if _free_slot() < 0:
				show_message("合成栏已满", true)
				break
			_place_from_backpack(i)
			if _backpack.slots[i] == null:
				break
	_rarity_menu.visible = false
	_refresh()

func _on_changed() -> void:
	if _open:
		_refresh()
