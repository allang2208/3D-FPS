extends Control
## 背包 HUD（从旧 2D 项目 QuickBar + EquipManager 背包面板迁移到 Godot 4）
##
## 布局（全部代码构建，遵循项目"少手写 .tscn"约定）：
## - 底部快捷栏：1~4 号槽（旧版 itemGroup），数字键/左键使用，拖拽绑定/交换
## - Tab / B：背包面板（36 格，旧版 inventory-grid 6 列）
## - 右键背包格 = 使用消耗品；格间拖拽 = 交换；拖出快捷栏到背包格 = 解绑
##
## 数据层在 ui/backpack.gd，本脚本只负责展示与输入。

signal player_healed(hp: int)

const BackpackScript := preload("res://ui/backpack.gd")

const HOTBAR_SIZE := 4
const SLOT_COLS := 6
const HOTBAR_SLOT := 52
const CELL_SLOT := 64
const BAR_PAD := 8
const BAR_GAP := 8

var backpack: BackpackScript

var _hotbar_root: HBoxContainer
var _hotbar_slots: Array = []
var _grid: GridContainer
var _cells: Array = []
var _panel_root: Control
var _panel_open := false
var _count_label: Label
var _status_label: Label
var _status_timer: Timer
var _tex_cache := {}

const COLOR_BAR_BG := Color(0.16, 0.145, 0.125, 0.94)
const COLOR_BAR_BORDER := Color(0.353, 0.302, 0.247)
const COLOR_SLOT_BG := Color(0.239, 0.204, 0.169)
const COLOR_SLOT_BORDER := Color(0.353, 0.302, 0.247)
const COLOR_ITEM_BG := Color(0.239, 0.29, 0.208)
const COLOR_ITEM_BORDER := Color(0.478, 0.604, 0.416)
const COLOR_TEXT := Color(0.831, 0.773, 0.659)
const COLOR_DIM_TEXT := Color(0.545, 0.478, 0.408)

func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	var theme := Theme.new()
	var font := SystemFont.new()
	font.font_names = PackedStringArray(["Microsoft YaHei", "SimHei", "Noto Sans CJK SC"])
	theme.default_font = font
	theme.default_font_size = 13
	set_theme(theme)
	_build_status_label()
	_status_timer = Timer.new()
	_status_timer.one_shot = true
	_status_timer.timeout.connect(func() -> void: _status_label.visible = false)
	add_child(_status_timer)
	_build_hotbar()
	_build_panel()

func setup(bp: RefCounted) -> void:
	backpack = bp
	backpack.changed.connect(_refresh)
	_refresh()

## 背包数据变化后重建两个区域（数据量小，直接重建最稳）
func _refresh() -> void:
	if backpack == null:
		return
	_refresh_hotbar()
	_refresh_grid()
	if _count_label != null:
		_count_label.text = "%d/%d" % [backpack.item_count(), backpack.max_slots]

func _refresh_hotbar() -> void:
	for i in _hotbar_slots.size():
		var slot: HotbarSlot = _hotbar_slots[i]
		var item := backpack.resolve_hotbar(i)
		var icon := slot.get_node("Content/Icon") as TextureRect
		var stack := slot.get_node("Content/Stack") as Label
		if item.is_empty():
			icon.texture = null
			stack.text = ""
			slot.add_theme_stylebox_override("panel", _make_style(COLOR_SLOT_BG, COLOR_SLOT_BORDER, 8, 2))
			slot.tooltip_text = "快捷栏 %d（空）" % (i + 1)
		else:
			icon.texture = _icon_tex(String(item.get("icon", "")))
			var count: int = item.get("stack", 0)
			stack.text = str(count)
			stack.add_theme_color_override("font_color", Color(0.95, 0.35, 0.32) if count <= 0 else COLOR_TEXT)
			slot.add_theme_stylebox_override("panel", _make_style(COLOR_ITEM_BG, COLOR_ITEM_BORDER, 8, 2))
			slot.tooltip_text = "%s × %d\n%s" % [String(item.get("name", "")), count, String(item.get("desc", ""))]

func _refresh_grid() -> void:
	for i in _cells.size():
		var cell: BackpackCell = _cells[i]
		var icon := cell.get_node("Content/Icon") as TextureRect
		var name_lbl := cell.get_node("Content/Name") as Label
		var stack_lbl := cell.get_node("Content/Stack") as Label
		if backpack.slots[i] == null:
			icon.texture = null
			name_lbl.text = ""
			stack_lbl.text = ""
			cell.add_theme_stylebox_override("panel", _make_style(COLOR_SLOT_BG, COLOR_SLOT_BORDER, 8, 2))
			cell.tooltip_text = "空"
		else:
			var item: Dictionary = backpack.slots[i]
			icon.texture = _icon_tex(String(item.get("icon", "")))
			name_lbl.text = String(item.get("name", ""))
			var count: int = item.get("stack", 1)
			stack_lbl.text = str(count) if count > 1 else ""
			cell.add_theme_stylebox_override("panel", _make_style(COLOR_ITEM_BG, COLOR_ITEM_BORDER, 8, 2))
			cell.tooltip_text = "%s × %d\n%s" % [String(item.get("name", "")), count, String(item.get("desc", ""))]

## ---------- 输入 ----------

func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and not event.echo:
		match event.keycode:
			KEY_1, KEY_2, KEY_3, KEY_4:
				use_hotbar(event.keycode - KEY_1)
			KEY_TAB, KEY_B:
				toggle_panel()
			KEY_ESCAPE:
				if _panel_open:
					set_panel_open(false)

func use_hotbar(index: int) -> void:
	if backpack == null or _panel_open:
		return
	var player := _get_player()
	if player == null or bool(player.get("is_dead")):
		return
	var result := backpack.use_hotbar(index, player)
	if result.get("ok", false):
		_notify_heal(player)
	_flash_status(String(result.get("message", "")))

func use_backpack_item(slot: int) -> void:
	if backpack == null or slot < 0 or slot >= backpack.slots.size() or backpack.slots[slot] == null:
		return
	var item: Dictionary = backpack.slots[slot]
	var player := _get_player()
	if player == null or bool(player.get("is_dead")):
		return
	var result := backpack.use_item(String(item.get("instance_id", "")), player)
	if result.get("ok", false):
		_notify_heal(player)
	_flash_status(String(result.get("message", "")))

func _notify_heal(player: Node) -> void:
	if player != null and player.get("hp") != null:
		player_healed.emit(int(player.get("hp")))

func toggle_panel() -> void:
	set_panel_open(not _panel_open)

func set_panel_open(open: bool) -> void:
	_panel_open = open
	_panel_root.visible = open
	if open:
		Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	else:
		var player := _get_player()
		if player == null or not bool(player.get("is_dead")):
			Input.mouse_mode = Input.MOUSE_MODE_CAPTURED

func _get_player() -> Node:
	var scene := get_tree().current_scene
	if scene == null:
		return null
	return scene.get_node_or_null("Player")

## ---------- 拖拽落点 ----------

func drop_on_hotbar(index: int, data: Dictionary) -> void:
	if backpack == null:
		return
	match String(data.get("type", "")):
		"hotbar":
			backpack.swap_hotbar(index, int(data.get("index", -1)))
		"backpack":
			var src := int(data.get("slot", -1))
			if src >= 0 and src < backpack.slots.size() and backpack.slots[src] != null:
				backpack.bind_hotbar(index, String(backpack.slots[src].get("instance_id", "")))

func drop_on_backpack(slot: int, data: Dictionary) -> void:
	if backpack == null:
		return
	match String(data.get("type", "")):
		"backpack":
			backpack.swap_items(slot, int(data.get("slot", -1)))
		"hotbar":
			backpack.unbind_hotbar(int(data.get("index", -1)))

## ---------- 构建 ----------

func _build_hotbar() -> void:
	var bar := PanelContainer.new()
	bar.name = "Hotbar"
	bar.mouse_filter = Control.MOUSE_FILTER_IGNORE
	bar.add_theme_stylebox_override("panel", _make_style(COLOR_BAR_BG, COLOR_BAR_BORDER, 12, 2))
	bar.add_theme_constant_override("margin_left", BAR_PAD)
	bar.add_theme_constant_override("margin_right", BAR_PAD)
	bar.add_theme_constant_override("margin_top", BAR_PAD)
	bar.add_theme_constant_override("margin_bottom", BAR_PAD)
	add_child(bar)
	_hotbar_root = HBoxContainer.new()
	_hotbar_root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_hotbar_root.add_theme_constant_override("separation", BAR_GAP)
	bar.add_child(_hotbar_root)
	for i in HOTBAR_SIZE:
		var slot := HotbarSlot.new()
		slot.hud = self
		slot.index = i
		slot.custom_minimum_size = Vector2(HOTBAR_SLOT, HOTBAR_SLOT)
		slot.add_theme_stylebox_override("panel", _make_style(COLOR_SLOT_BG, COLOR_SLOT_BORDER, 8, 2))
		var content := Control.new()
		content.name = "Content"
		content.custom_minimum_size = Vector2(HOTBAR_SLOT, HOTBAR_SLOT)
		slot.add_child(content)
		var icon := TextureRect.new()
		icon.name = "Icon"
		icon.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT, Control.PRESET_MODE_MINSIZE, 3)
		icon.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		icon.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
		icon.mouse_filter = Control.MOUSE_FILTER_IGNORE
		content.add_child(icon)
		var stack := _make_label(content, "", 11, COLOR_TEXT, Vector2(3, HOTBAR_SLOT - 17))
		stack.name = "Stack"
		var key := _make_label(content, str(i + 1), 10, Color(0.9, 0.9, 0.9), Vector2(HOTBAR_SLOT - 14, HOTBAR_SLOT - 17))
		key.name = "Key"
		_hotbar_root.add_child(slot)
		_hotbar_slots.append(slot)
	var w := HOTBAR_SIZE * HOTBAR_SLOT + (HOTBAR_SIZE - 1) * BAR_GAP + BAR_PAD * 2
	var h := HOTBAR_SLOT + BAR_PAD * 2
	bar.anchor_left = 0.5
	bar.anchor_right = 0.5
	bar.anchor_top = 1.0
	bar.anchor_bottom = 1.0
	bar.grow_horizontal = Control.GROW_DIRECTION_BOTH
	bar.grow_vertical = Control.GROW_DIRECTION_BOTH
	bar.offset_left = -w / 2.0
	bar.offset_right = w / 2.0
	bar.offset_top = -h - 14.0
	bar.offset_bottom = -14.0

func _build_panel() -> void:
	_panel_root = Control.new()
	_panel_root.name = "BackpackPanel"
	_panel_root.mouse_filter = Control.MOUSE_FILTER_STOP
	_panel_root.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	_panel_root.visible = false
	add_child(_panel_root)
	var dim := ColorRect.new()
	dim.color = Color(0, 0, 0, 0.35)
	dim.mouse_filter = Control.MOUSE_FILTER_IGNORE
	dim.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	_panel_root.add_child(dim)
	var center := CenterContainer.new()
	center.mouse_filter = Control.MOUSE_FILTER_IGNORE
	center.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	_panel_root.add_child(center)
	var panel := PanelContainer.new()
	panel.mouse_filter = Control.MOUSE_FILTER_STOP
	panel.add_theme_stylebox_override("panel", _make_style(Color(0.13, 0.12, 0.10, 0.97), COLOR_BAR_BORDER, 12, 2))
	center.add_child(panel)
	var vbox := VBoxContainer.new()
	vbox.add_theme_constant_override("separation", 10)
	panel.add_child(vbox)
	var title_row := HBoxContainer.new()
	vbox.add_child(title_row)
	var title := _make_label(title_row, "背包", 20, Color(0.91, 0.87, 0.8), Vector2.ZERO)
	title.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_count_label = _make_label(title_row, "", 14, COLOR_DIM_TEXT, Vector2.ZERO)
	_grid = GridContainer.new()
	_grid.columns = SLOT_COLS
	_grid.add_theme_constant_override("h_separation", 6)
	_grid.add_theme_constant_override("v_separation", 6)
	vbox.add_child(_grid)
	var total_slots := backpack.max_slots if backpack != null else 36
	for i in total_slots:
		var cell := BackpackCell.new()
		cell.hud = self
		cell.slot = i
		cell.custom_minimum_size = Vector2(CELL_SLOT, CELL_SLOT)
		cell.add_theme_stylebox_override("panel", _make_style(COLOR_SLOT_BG, COLOR_SLOT_BORDER, 8, 2))
		var content := Control.new()
		content.name = "Content"
		content.custom_minimum_size = Vector2(CELL_SLOT, CELL_SLOT)
		cell.add_child(content)
		var icon := TextureRect.new()
		icon.name = "Icon"
		icon.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT, Control.PRESET_MODE_MINSIZE, 5)
		icon.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		icon.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
		icon.mouse_filter = Control.MOUSE_FILTER_IGNORE
		content.add_child(icon)
		var stack := _make_label(content, "", 12, Color(0.95, 0.9, 0.8), Vector2(CELL_SLOT - 20, 4))
		stack.name = "Stack"
		var name_lbl := _make_label(content, "", 10, Color.WHITE, Vector2(3, CELL_SLOT - 15))
		name_lbl.name = "Name"
		name_lbl.custom_minimum_size = Vector2(CELL_SLOT - 6, 12)
		name_lbl.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		_grid.add_child(cell)
		_cells.append(cell)

func _build_status_label() -> void:
	_status_label = _make_label(self, "", 14, Color(0.98, 0.75, 0.4), Vector2.ZERO)
	_status_label.set_anchors_and_offsets_preset(Control.PRESET_CENTER_BOTTOM)
	_status_label.offset_top = -92
	_status_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_status_label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	_status_label.visible = false

## ---------- 工具 ----------

func _make_style(bg: Color, border: Color, radius: int, border_w: int) -> StyleBoxFlat:
	var sb := StyleBoxFlat.new()
	sb.bg_color = bg
	sb.border_color = border
	sb.set_border_width_all(border_w)
	sb.set_corner_radius_all(radius)
	return sb

func _make_label(parent: Node, text: String, font_size: int, color: Color, pos: Vector2) -> Label:
	var l := Label.new()
	l.text = text
	l.position = pos
	l.add_theme_font_size_override("font_size", font_size)
	l.add_theme_color_override("font_color", color)
	l.mouse_filter = Control.MOUSE_FILTER_IGNORE
	parent.add_child(l)
	return l

func _icon_tex(path: String) -> Texture2D:
	if path == "":
		return null
	if not _tex_cache.has(path):
		var res := load(path)
		_tex_cache[path] = res if res is Texture2D else null
	return _tex_cache[path]

func make_slot_preview(item: Dictionary) -> Control:
	var p := PanelContainer.new()
	p.custom_minimum_size = Vector2(44, 44)
	p.add_theme_stylebox_override("panel", _make_style(Color(0.2, 0.18, 0.15, 0.92), COLOR_ITEM_BORDER, 6, 2))
	var tr := TextureRect.new()
	tr.texture = _icon_tex(String(item.get("icon", "")))
	tr.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	tr.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	p.add_child(tr)
	return p

func _flash_status(text: String) -> void:
	if _status_label == null or text == "":
		return
	_status_label.text = text
	_status_label.visible = true
	_status_timer.start(1.6)

## ---------- 内部控件 ----------

class HotbarSlot:
	extends PanelContainer

	var hud
	var index := 0
	var _press_pos := Vector2.ZERO
	var _pressed := false

	func _ready() -> void:
		mouse_filter = Control.MOUSE_FILTER_STOP

	func _gui_input(event: InputEvent) -> void:
		if event is InputEventMouseButton and event.button_index == MOUSE_BUTTON_LEFT:
			if event.pressed:
				_pressed = true
				_press_pos = get_global_mouse_position()
			elif _pressed:
				_pressed = false
				if get_global_mouse_position().distance_to(_press_pos) < 8.0:
					hud.use_hotbar(index)

	func _get_drag_data(_at: Vector2):
		var item = hud.backpack.resolve_hotbar(index)
		if item.is_empty():
			return null
		hud.set_drag_preview(hud.make_slot_preview(item))
		return {"type": "hotbar", "index": index}

	func _can_drop_data(_at: Vector2, data) -> bool:
		return data is Dictionary and (String(data.get("type", "")) == "hotbar" or String(data.get("type", "")) == "backpack")

	func _drop_data(_at: Vector2, data) -> void:
		hud.drop_on_hotbar(index, data)

class BackpackCell:
	extends PanelContainer

	var hud
	var slot := 0

	func _ready() -> void:
		mouse_filter = Control.MOUSE_FILTER_STOP

	func _gui_input(event: InputEvent) -> void:
		if event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_RIGHT:
			hud.use_backpack_item(slot)

	func _get_drag_data(_at: Vector2):
		if hud.backpack == null or hud.backpack.slots[slot] == null:
			return null
		hud.set_drag_preview(hud.make_slot_preview(hud.backpack.slots[slot]))
		return {"type": "backpack", "slot": slot}

	func _can_drop_data(_at: Vector2, data) -> bool:
		return data is Dictionary and (String(data.get("type", "")) == "backpack" or String(data.get("type", "")) == "hotbar")

	func _drop_data(_at: Vector2, data) -> void:
		hud.drop_on_backpack(slot, data)
