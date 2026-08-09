extends Control
## 背包 HUD（从旧 2D 项目 QuickBar + EquipManager 背包面板迁移到 Godot 4）
##
## 布局（全部代码构建，遵循项目"少手写 .tscn"约定）：
## - 底部快捷栏：1~4 号槽（旧版 itemGroup），数字键/左键使用，拖拽绑定/交换
## - Tab / B：背包面板（36 格，旧版 inventory-grid 6 列）
## - 右键背包格 = 使用消耗品；格间拖拽 = 交换；拖出快捷栏到背包格 = 解绑
##
## 复刻的旧版弹出效果：
## - 面板从右侧滑入 + 遮罩淡入 + 毛玻璃背景（panel_blur.gdshader）
## - 新物品 equipPop（0.5→1.2→0.95→1）、绑定 equipFlash（scale 脉冲）
## - 快捷栏数字键闪烁（keyHintBlink）、0 数量点击抖动、冷却遮罩
## - 悬停高亮 + 拖拽目标高亮（旧版 .drag-over）
## - 物品浮窗（item_tooltip.gd）：悬停跟随、点击固定、贴边翻转、关闭按钮
## - 背包已满提示（旧版 backpackFullNotice，顶部淡出）

signal player_healed(hp: int)

const BackpackScript := preload("res://ui/backpack.gd")
const Style := preload("res://ui/style.gd")
const ItemTooltipScript := preload("res://ui/item_tooltip.gd")
const PANEL_BLUR_SHADER := preload("res://assets/ui/shaders/panel_blur.gdshader")

const HOTBAR_SIZE := 4
const SLOT_COLS := 6
const HOTBAR_SLOT := 52
const CELL_SLOT := 64
const BAR_PAD := 8
const BAR_GAP := 8
const PANEL_MARGIN := 14
const PANEL_SLIDE_X := 140.0

var backpack: BackpackScript

var _hotbar_root: HBoxContainer
var _hotbar_slots: Array = []
var _grid: GridContainer
var _cells: Array = []
var _panel_root: Control
var _panel: PanelContainer
var _panel_base_pos := Vector2.ZERO
var _panel_anim: Tween
var _panel_open := false
var _count_label: Label
var _status_label: Label
var _notice_label: Label
var _status_timer: Timer
var _notice_tween: Tween
var _drag_clear_timer: Timer
var _tooltip: Control
var _tooltip_tween: Tween
var _tex_cache := {}
var _cd_last := {}
var _hovered_cell := -1
var _hovered_hotbar := -1

var _s_hotbar_empty: StyleBoxFlat
var _s_hotbar_item: StyleBoxFlat
var _s_hotbar_hover: StyleBoxFlat
var _s_cell_empty: StyleBoxFlat
var _s_cell_item: StyleBoxFlat
var _s_cell_hover: StyleBoxFlat
var _s_cell_drag_over: StyleBoxFlat

func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	theme = Style.make_theme()
	_s_hotbar_empty = Style.make_style(Style.COLOR_SLOT_BG, Style.COLOR_SLOT_BORDER, 8, 2)
	_s_hotbar_item = Style.make_style(Style.COLOR_ITEM_BG, Style.COLOR_ITEM_BORDER, 8, 2)
	_s_hotbar_hover = Style.make_style(Style.COLOR_SLOT_HOVER_BG, Style.COLOR_SLOT_HOVER_BORDER, 8, 2)
	_s_cell_empty = Style.make_style(Style.COLOR_SLOT_BG, Style.COLOR_SLOT_BORDER, 8, 2)
	_s_cell_item = Style.make_style(Style.COLOR_ITEM_BG, Style.COLOR_ITEM_BORDER, 8, 2)
	_s_cell_hover = Style.make_style(Style.COLOR_SLOT_HOVER_BG, Style.COLOR_SLOT_HOVER_BORDER, 8, 2)
	_s_cell_drag_over = Style.make_style(Style.COLOR_DRAG_OVER_BG, Style.COLOR_DRAG_OVER_BORDER, 8, 2)
	_build_status_label()
	_status_timer = Timer.new()
	_status_timer.one_shot = true
	_status_timer.timeout.connect(func() -> void: _status_label.visible = false)
	add_child(_status_timer)
	_drag_clear_timer = Timer.new()
	_drag_clear_timer.one_shot = true
	_drag_clear_timer.timeout.connect(_clear_all_drag_over)
	add_child(_drag_clear_timer)
	_build_hotbar()
	_build_panel()
	_build_tooltip()
	_build_notice()

func setup(bp: BackpackScript) -> void:
	backpack = bp
	backpack.changed.connect(_refresh)
	backpack.item_added.connect(_on_item_added)
	backpack.bound.connect(_on_bound)
	_refresh()

## ---------- 数据变化刷新 ----------

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
			slot.add_theme_stylebox_override("panel", _s_hotbar_hover if i == _hovered_hotbar else _s_hotbar_empty)
			slot.tooltip_text = ""
		else:
			icon.texture = _icon_tex(String(item.get("icon", "")))
			var count: int = item.get("stack", 0)
			stack.text = str(count)
			stack.add_theme_color_override("font_color", Color(0.95, 0.35, 0.32) if count <= 0 else Style.COLOR_TEXT)
			slot.add_theme_stylebox_override("panel", _s_hotbar_hover if i == _hovered_hotbar else _s_hotbar_item)
			slot.tooltip_text = ""

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
			cell.add_theme_stylebox_override("panel", _s_cell_hover if i == _hovered_cell else _s_cell_empty)
			cell.tooltip_text = ""
		else:
			var item: Dictionary = backpack.slots[i]
			icon.texture = _icon_tex(String(item.get("icon", "")))
			name_lbl.text = String(item.get("name", ""))
			var count: int = item.get("stack", 1)
			stack_lbl.text = str(count) if count > 1 else ""
			cell.add_theme_stylebox_override("panel", _s_cell_drag_over if i == _drag_over_cell else (_s_cell_hover if i == _hovered_cell else _s_cell_item))
			cell.tooltip_text = ""

## ---------- 输入 ----------

func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and not event.echo:
		match event.keycode:
			KEY_1, KEY_2, KEY_3, KEY_4:
				use_hotbar(event.keycode - KEY_1)
			KEY_TAB, KEY_B:
				toggle_panel()
			KEY_ESCAPE:
				if _tooltip != null and _tooltip.visible:
					hide_tooltip()
				elif _panel_open:
					set_panel_open(false)
	elif event is InputEventMouseButton and event.pressed:
		if _tooltip != null and _tooltip.is_pinned():
			var m := get_viewport().get_mouse_position()
			if not _tooltip.get_global_rect().has_point(m):
				hide_tooltip()

func use_hotbar(index: int) -> void:
	if backpack == null or _panel_open:
		return
	var player := _get_player()
	if player == null or bool(player.get("is_dead")):
		return
	var item := backpack.resolve_hotbar(index)
	if item.is_empty():
		return
	if int(item.get("stack", 0)) <= 0:
		_shake_hotbar(index)
		return
	var result := backpack.use_hotbar(index, player)
	if result.get("ok", false):
		_notify_heal(player)
	else:
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
	else:
		_flash_status(String(result.get("message", "")))

func _notify_heal(player: Node) -> void:
	if player != null and player.get("hp") != null:
		player_healed.emit(int(player.get("hp")))

## ---------- 面板开关（右侧滑入 + 遮罩淡入） ----------

func toggle_panel() -> void:
	set_panel_open(not _panel_open)

func set_panel_open(open: bool) -> void:
	if _panel_open == open:
		return
	_panel_open = open
	if _panel_anim != null and _panel_anim.is_valid():
		_panel_anim.kill()
	var dim := _panel_root.get_node("Dim") as ColorRect
	if open:
		_panel_root.visible = true
		dim.modulate.a = 0.0
		_panel.modulate.a = 0.0
		_panel.position = _panel_base_pos + Vector2(PANEL_SLIDE_X, 0)
		_panel_anim = create_tween()
		_panel_anim.tween_property(dim, "modulate:a", 1.0, 0.22)
		_panel_anim.parallel().tween_property(_panel, "position", _panel_base_pos, 0.24) \
			.set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_OUT)
		_panel_anim.parallel().tween_property(_panel, "modulate:a", 1.0, 0.18)
		Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	else:
		_panel_anim = create_tween()
		_panel_anim.tween_property(dim, "modulate:a", 0.0, 0.16)
		_panel_anim.parallel().tween_property(_panel, "position", _panel_base_pos + Vector2(PANEL_SLIDE_X, 0), 0.18) \
			.set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_IN)
		_panel_anim.parallel().tween_property(_panel, "modulate:a", 0.0, 0.14)
		_panel_anim.tween_callback(func() -> void: _panel_root.visible = false)
		var player := _get_player()
		if player == null or not bool(player.get("is_dead")):
			Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
	hide_tooltip()

## ---------- 获取/添加物品 ----------

func try_add(id: String, count := 1) -> bool:
	if backpack == null:
		return false
	var ok := backpack.add_item(id, count)
	if not ok:
		_show_notice("背包已满")
	return ok

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

## ---------- 动画回调 ----------

func _on_item_added(slot: int) -> void:
	if slot >= 0 and slot < _cells.size():
		_pop_cell(slot)

func _on_bound(index: int) -> void:
	if index >= 0 and index < _hotbar_slots.size():
		_flash_hotbar(index)

func _pop_cell(slot: int) -> void:
	var cell: BackpackCell = _cells[slot]
	cell.pivot_offset = Vector2(CELL_SLOT, CELL_SLOT) * 0.5
	var tw := create_tween()
	tw.tween_property(cell, "scale", Vector2(1.2, 1.2), 0.18).from(Vector2(0.5, 0.5))
	tw.tween_property(cell, "scale", Vector2(0.95, 0.95), 0.12)
	tw.tween_property(cell, "scale", Vector2.ONE, 0.12)

func _flash_hotbar(index: int) -> void:
	var slot: HotbarSlot = _hotbar_slots[index]
	slot.pivot_offset = Vector2(HOTBAR_SLOT, HOTBAR_SLOT) * 0.5
	var tw := create_tween()
	tw.tween_property(slot, "scale", Vector2(1.15, 1.15), 0.14)
	tw.tween_property(slot, "scale", Vector2.ONE, 0.16).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)

func _shake_hotbar(index: int) -> void:
	var slot: HotbarSlot = _hotbar_slots[index]
	slot.pivot_offset = Vector2(HOTBAR_SLOT, HOTBAR_SLOT) * 0.5
	var tw := create_tween()
	tw.tween_property(slot, "scale", Vector2(0.95, 0.95), 0.06)
	tw.tween_property(slot, "scale", Vector2.ONE, 0.1).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)

func _flash_cd_end(slot: HotbarSlot) -> void:
	var overlay := slot.get_node("Content/CD") as ColorRect
	overlay.color = Color(1, 1, 1, 0.85)
	var tw := create_tween()
	tw.tween_property(overlay, "color", Color(0, 0, 0, 0.55), 0.18)

## ---------- 悬停 / 拖拽高亮 ----------

var _drag_over_cell := -1
var _drag_over_hotbar := -1

func on_cell_mouse(enter: bool, slot: int) -> void:
	if slot < 0 or slot >= _cells.size():
		return
	_hovered_cell = slot if enter else -1
	var cell: BackpackCell = _cells[slot]
	if enter:
		cell.add_theme_stylebox_override("panel", _s_cell_drag_over if slot == _drag_over_cell else _s_cell_hover)
		if backpack != null and backpack.slots[slot] != null:
			show_item_tooltip(backpack.slots[slot], get_viewport().get_mouse_position())
	else:
		cell.add_theme_stylebox_override("panel", _s_cell_drag_over if slot == _drag_over_cell else (_s_cell_item if backpack.slots[slot] != null else _s_cell_empty))
		if _tooltip != null and not _tooltip.is_pinned():
			hide_tooltip()

func on_hotbar_mouse(enter: bool, index: int) -> void:
	if index < 0 or index >= _hotbar_slots.size():
		return
	_hovered_hotbar = index if enter else -1
	var slot: HotbarSlot = _hotbar_slots[index]
	var item := backpack.resolve_hotbar(index) if backpack != null else {}
	if enter:
		slot.add_theme_stylebox_override("panel", _s_hotbar_hover)
		if not item.is_empty():
			show_item_tooltip(item, get_viewport().get_mouse_position())
	else:
		slot.add_theme_stylebox_override("panel", _s_hotbar_item if not item.is_empty() else _s_hotbar_empty)
		if _tooltip != null and not _tooltip.is_pinned():
			hide_tooltip()

func set_cell_drag_over(slot: int, on: bool) -> void:
	if slot < 0 or slot >= _cells.size():
		return
	_drag_over_cell = slot if on else -1
	var cell: BackpackCell = _cells[slot]
	if on:
		cell.add_theme_stylebox_override("panel", _s_cell_drag_over)
		_drag_clear_timer.start(0.25)
	else:
		cell.add_theme_stylebox_override("panel", _s_cell_hover if slot == _hovered_cell else (_s_cell_item if backpack.slots[slot] != null else _s_cell_empty))

func set_hotbar_drag_over(index: int, on: bool) -> void:
	if index < 0 or index >= _hotbar_slots.size():
		return
	_drag_over_hotbar = index if on else -1
	var slot: HotbarSlot = _hotbar_slots[index]
	var item := backpack.resolve_hotbar(index) if backpack != null else {}
	if on:
		slot.add_theme_stylebox_override("panel", _s_hotbar_hover)
		_drag_clear_timer.start(0.25)
	else:
		slot.add_theme_stylebox_override("panel", _s_hotbar_item if not item.is_empty() else _s_hotbar_empty)

func _clear_all_drag_over() -> void:
	if backpack == null:
		return
	_drag_over_cell = -1
	_drag_over_hotbar = -1
	for i in _cells.size():
		var cell: BackpackCell = _cells[i]
		cell.add_theme_stylebox_override("panel", _s_cell_hover if i == _hovered_cell else (_s_cell_item if backpack.slots[i] != null else _s_cell_empty))
	for i in _hotbar_slots.size():
		var slot: HotbarSlot = _hotbar_slots[i]
		var item := backpack.resolve_hotbar(i) if backpack != null else {}
		slot.add_theme_stylebox_override("panel", _s_hotbar_item if not item.is_empty() else _s_hotbar_empty)

func on_cell_click_pin(slot: int) -> void:
	if _tooltip == null or backpack == null or backpack.slots[slot] == null:
		return
	show_item_tooltip(backpack.slots[slot], get_viewport().get_mouse_position())
	_tooltip.set_pinned(true)

## ---------- 浮窗 ----------

func _build_tooltip() -> void:
	_tooltip = ItemTooltipScript.new()
	_tooltip.name = "ItemTooltip"
	_tooltip.visible = false
	_tooltip.close_requested.connect(hide_tooltip)
	add_child(_tooltip)

func show_item_tooltip(item: Dictionary, at_pos: Vector2) -> void:
	if _tooltip == null or item.is_empty():
		return
	_tooltip.render(item)
	_tooltip.set_pinned(false)
	_tooltip.visible = true
	_tooltip.modulate.a = 1.0
	if _tooltip_tween != null and _tooltip_tween.is_valid():
		_tooltip_tween.kill()
	_tooltip_tween = create_tween()
	_tooltip_tween.tween_property(_tooltip, "modulate:a", 1.0, 0.12).from(0.0)
	_place_tooltip(at_pos)

func hide_tooltip() -> void:
	if _tooltip == null or not _tooltip.visible:
		return
	if _tooltip_tween != null and _tooltip_tween.is_valid():
		_tooltip_tween.kill()
	_tooltip_tween = create_tween()
	_tooltip_tween.tween_property(_tooltip, "modulate:a", 0.0, 0.1)
	_tooltip_tween.tween_callback(func() -> void: _tooltip.visible = false)

func _place_tooltip(at: Vector2) -> void:
	if _tooltip == null:
		return
	var ts := _tooltip.get_combined_minimum_size()
	var vp := get_viewport_rect().size
	var pos := at + Vector2(16, 16)
	if pos.x + ts.x > vp.x - 8:
		pos.x = at.x - ts.x - 12
	if pos.y + ts.y > vp.y - 8:
		pos.y = at.y - ts.y - 12
	pos.x = clampf(pos.x, 8, maxf(8, vp.x - ts.x - 8))
	pos.y = clampf(pos.y, 8, maxf(8, vp.y - ts.y - 8))
	_tooltip.position = pos

## ---------- 冷却 ----------

func _process(delta: float) -> void:
	if backpack != null:
		backpack.tick_cooldowns(delta)
		_update_cooldown_overlays()
	if _tooltip != null and _tooltip.visible and not _tooltip.is_pinned():
		_place_tooltip(get_viewport().get_mouse_position())

func _update_cooldown_overlays() -> void:
	for i in _hotbar_slots.size():
		var slot: HotbarSlot = _hotbar_slots[i]
		var overlay := slot.get_node("Content/CD") as ColorRect
		var item := backpack.resolve_hotbar(i)
		if item.is_empty():
			overlay.visible = false
			_cd_last[i] = 0.0
			continue
		var inst := String(item.get("instance_id", ""))
		var remaining := backpack.get_cooldown(inst)
		var total := backpack.get_cooldown_total(inst)
		var prev := float(_cd_last.get(i, 0.0))
		if total > 0.0 and remaining > 0.0:
			var pct := clampf(remaining / total, 0.0, 1.0)
			overlay.visible = true
			overlay.offset_top = -HOTBAR_SLOT * pct
			overlay.color = Color(0, 0, 0, 0.55)
		elif prev > 0.0 and remaining <= 0.0:
			overlay.visible = true
			_flash_cd_end(slot)
		else:
			overlay.visible = false
		_cd_last[i] = remaining

## ---------- 构建：快捷栏 ----------

func _build_hotbar() -> void:
	var bar := PanelContainer.new()
	bar.name = "Hotbar"
	bar.mouse_filter = Control.MOUSE_FILTER_IGNORE
	bar.add_theme_stylebox_override("panel", Style.make_style(Style.COLOR_BAR_BG, Style.COLOR_BAR_BORDER, 12, 2))
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
		slot.add_theme_stylebox_override("panel", _s_hotbar_empty)
		var content := Control.new()
		content.name = "Content"
		content.custom_minimum_size = Vector2(HOTBAR_SLOT, HOTBAR_SLOT)
		content.mouse_filter = Control.MOUSE_FILTER_IGNORE
		slot.add_child(content)
		var icon := TextureRect.new()
		icon.name = "Icon"
		icon.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT, Control.PRESET_MODE_MINSIZE, 3)
		icon.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		icon.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
		icon.mouse_filter = Control.MOUSE_FILTER_IGNORE
		content.add_child(icon)
		var stack := _make_label(content, "", 11, Style.COLOR_TEXT, Vector2(3, HOTBAR_SLOT - 17))
		stack.name = "Stack"
		var key := _make_label(content, str(i + 1), 10, Color(0.9, 0.9, 0.9), Vector2(HOTBAR_SLOT - 14, HOTBAR_SLOT - 17))
		key.name = "Key"
		var blink := create_tween()
		blink.set_loops()
		blink.tween_property(key, "modulate:a", 0.35, 0.6).set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
		blink.tween_property(key, "modulate:a", 1.0, 0.6).set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
		var cd := ColorRect.new()
		cd.name = "CD"
		cd.color = Color(0, 0, 0, 0.55)
		cd.mouse_filter = Control.MOUSE_FILTER_IGNORE
		cd.anchor_left = 0.0
		cd.anchor_right = 1.0
		cd.anchor_top = 1.0
		cd.anchor_bottom = 1.0
		cd.offset_left = 0
		cd.offset_right = 0
		cd.offset_bottom = 0
		cd.offset_top = 0
		cd.visible = false
		content.add_child(cd)
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

## ---------- 构建：背包面板（右侧滑入 + 毛玻璃） ----------

func _build_panel() -> void:
	_panel_root = Control.new()
	_panel_root.name = "BackpackPanel"
	_panel_root.mouse_filter = Control.MOUSE_FILTER_STOP
	_panel_root.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	_panel_root.visible = false
	add_child(_panel_root)
	var dim := ColorRect.new()
	dim.name = "Dim"
	dim.color = Style.COLOR_OVERLAY
	dim.mouse_filter = Control.MOUSE_FILTER_IGNORE
	dim.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	_panel_root.add_child(dim)
	_panel = PanelContainer.new()
	_panel.name = "Panel"
	_panel.mouse_filter = Control.MOUSE_FILTER_STOP
	_panel.add_theme_stylebox_override("panel", Style.make_style(Style.COLOR_PANEL_BG, Style.COLOR_PANEL_BORDER, 12, 2))
	_panel_root.add_child(_panel)
	var content := Control.new()
	content.name = "Content"
	content.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_panel.add_child(content)
	var blur := ColorRect.new()
	blur.name = "Blur"
	blur.mouse_filter = Control.MOUSE_FILTER_IGNORE
	blur.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	var mat := ShaderMaterial.new()
	mat.shader = PANEL_BLUR_SHADER
	blur.material = mat
	content.add_child(blur)
	var margin := MarginContainer.new()
	margin.mouse_filter = Control.MOUSE_FILTER_IGNORE
	margin.add_theme_constant_override("margin_left", PANEL_MARGIN)
	margin.add_theme_constant_override("margin_right", PANEL_MARGIN)
	margin.add_theme_constant_override("margin_top", PANEL_MARGIN)
	margin.add_theme_constant_override("margin_bottom", PANEL_MARGIN)
	margin.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	content.add_child(margin)
	var vbox := VBoxContainer.new()
	vbox.add_theme_constant_override("separation", 10)
	margin.add_child(vbox)
	var title_row := HBoxContainer.new()
	vbox.add_child(title_row)
	var title := _make_label(title_row, "背包", 20, Color(0.91, 0.87, 0.8), Vector2.ZERO)
	title.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_count_label = _make_label(title_row, "", 14, Style.COLOR_DIM_TEXT, Vector2.ZERO)
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
		cell.add_theme_stylebox_override("panel", _s_cell_empty)
		var cell_content := Control.new()
		cell_content.name = "Content"
		cell_content.custom_minimum_size = Vector2(CELL_SLOT, CELL_SLOT)
		cell_content.mouse_filter = Control.MOUSE_FILTER_IGNORE
		cell.add_child(cell_content)
		var icon := TextureRect.new()
		icon.name = "Icon"
		icon.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT, Control.PRESET_MODE_MINSIZE, 5)
		icon.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		icon.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
		icon.mouse_filter = Control.MOUSE_FILTER_IGNORE
		cell_content.add_child(icon)
		var stack := _make_label(cell_content, "", 12, Color(0.95, 0.9, 0.8), Vector2(CELL_SLOT - 20, 4))
		stack.name = "Stack"
		var name_lbl := _make_label(cell_content, "", 10, Color.WHITE, Vector2(3, CELL_SLOT - 15))
		name_lbl.name = "Name"
		name_lbl.custom_minimum_size = Vector2(CELL_SLOT - 6, 12)
		name_lbl.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		_grid.add_child(cell)
		_cells.append(cell)
	content.custom_minimum_size = margin.get_combined_minimum_size()
	var s := _panel.get_combined_minimum_size()
	_panel_base_pos = Vector2(-s.x / 2.0, -s.y / 2.0)
	_panel.anchor_left = 0.5
	_panel.anchor_right = 0.5
	_panel.anchor_top = 0.5
	_panel.anchor_bottom = 0.5
	_panel.grow_horizontal = Control.GROW_DIRECTION_BOTH
	_panel.grow_vertical = Control.GROW_DIRECTION_BOTH
	_panel.offset_left = _panel_base_pos.x
	_panel.offset_right = s.x / 2.0
	_panel.offset_top = _panel_base_pos.y
	_panel.offset_bottom = s.y / 2.0

func _build_status_label() -> void:
	_status_label = _make_label(self, "", 14, Style.COLOR_STATUS, Vector2.ZERO)
	_status_label.set_anchors_and_offsets_preset(Control.PRESET_CENTER_BOTTOM)
	_status_label.offset_top = -92
	_status_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_status_label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	_status_label.visible = false

func _build_notice() -> void:
	_notice_label = _make_label(self, "", 22, Style.COLOR_NOTICE, Vector2.ZERO)
	_notice_label.set_anchors_and_offsets_preset(Control.PRESET_CENTER_TOP)
	_notice_label.offset_top = 210
	_notice_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_notice_label.visible = false

func _show_notice(text: String) -> void:
	if _notice_label == null:
		return
	_notice_label.text = text
	_notice_label.visible = true
	_notice_label.modulate.a = 1.0
	if _notice_tween != null and _notice_tween.is_valid():
		_notice_tween.kill()
	_notice_tween = create_tween()
	_notice_tween.tween_interval(1.2)
	_notice_tween.tween_property(_notice_label, "modulate:a", 0.0, 1.8)
	_notice_tween.tween_callback(func() -> void: _notice_label.visible = false)

## ---------- 工具 ----------

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
	p.add_theme_stylebox_override("panel", Style.make_style(Color(0.2, 0.18, 0.15, 0.92), Style.COLOR_ITEM_BORDER, 6, 2))
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
		mouse_entered.connect(func() -> void: hud.on_hotbar_mouse(true, index))
		mouse_exited.connect(func() -> void: hud.on_hotbar_mouse(false, index))

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
		hud.hide_tooltip()
		hud.set_drag_preview(hud.make_slot_preview(item))
		return {"type": "hotbar", "index": index}

	func _can_drop_data(_at: Vector2, data) -> bool:
		var ok := data is Dictionary and (String(data.get("type", "")) == "hotbar" or String(data.get("type", "")) == "backpack")
		if ok:
			hud.set_hotbar_drag_over(index, true)
		return ok

	func _drop_data(_at: Vector2, data) -> void:
		hud.set_hotbar_drag_over(index, false)
		hud.drop_on_hotbar(index, data)

class BackpackCell:
	extends PanelContainer

	var hud
	var slot := 0
	var _press_pos := Vector2.ZERO
	var _pressed := false

	func _ready() -> void:
		mouse_filter = Control.MOUSE_FILTER_STOP
		mouse_entered.connect(func() -> void: hud.on_cell_mouse(true, slot))
		mouse_exited.connect(func() -> void: hud.on_cell_mouse(false, slot))

	func _gui_input(event: InputEvent) -> void:
		if event is InputEventMouseButton:
			if event.button_index == MOUSE_BUTTON_LEFT:
				if event.pressed:
					_pressed = true
					_press_pos = get_global_mouse_position()
				elif _pressed:
					_pressed = false
					if get_global_mouse_position().distance_to(_press_pos) < 8.0:
						hud.on_cell_click_pin(slot)
			elif event.pressed and event.button_index == MOUSE_BUTTON_RIGHT:
				hud.use_backpack_item(slot)

	func _get_drag_data(_at: Vector2):
		if hud.backpack == null or hud.backpack.slots[slot] == null:
			return null
		hud.hide_tooltip()
		hud.set_drag_preview(hud.make_slot_preview(hud.backpack.slots[slot]))
		return {"type": "backpack", "slot": slot}

	func _can_drop_data(_at: Vector2, data) -> bool:
		var ok := data is Dictionary and (String(data.get("type", "")) == "backpack" or String(data.get("type", "")) == "hotbar")
		if ok:
			hud.set_cell_drag_over(slot, true)
		return ok

	func _drop_data(_at: Vector2, data) -> void:
		hud.set_cell_drag_over(slot, false)
		hud.drop_on_backpack(slot, data)
