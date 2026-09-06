extends CanvasLayer
## NPC 子面板基类（UI 迁移线）：商店/强化/改造/附魔/任务/祭坛共用。
## 居中面板 + 标题 + 金币 + 消息 + 关闭按钮；只消费 ui/style.gd Token。
## 子类实现 _build_body() 与 _refresh()，open() 时自动释放鼠标。

const Style := preload("res://ui/style.gd")

signal closed

var _shield: Control
var panel: Panel
var title_label: Label
var gold_label: Label
var message_label: Label
var body: VBoxContainer
var close_btn: Button
var economy: RefCounted
var _backpack
var _tooltip: PanelContainer

var _open := false
var _was_captured := false
var _msg_timer := 0.0
var _pending_title := ""

func _ready() -> void:
	layer = int(Style.npc("layer_panel", 60))
	_tooltip = load("res://ui/item_tooltip.gd").new()
	_tooltip.name = "ItemTooltip"
	_tooltip.visible = false
	add_child(_tooltip)
	_build()
	hide()

func _process(delta: float) -> void:
	if _msg_timer > 0.0:
		_msg_timer = maxf(0.0, _msg_timer - delta)
		if _msg_timer <= 0.0:
			message_label.text = ""
	if _tooltip != null and _tooltip.visible:
		var off := float(Style.npc("tooltip_offset", 16.0))
		_tooltip.position = get_viewport().get_mouse_position() + Vector2(off, off)

func _build() -> void:
	_shield = Control.new()
	_shield.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	_shield.mouse_filter = Control.MOUSE_FILTER_STOP
	add_child(_shield)
	var shade := ColorRect.new()
	shade.color = Style.COLOR_OVERLAY
	shade.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	shade.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_shield.add_child(shade)
	panel = Panel.new()
	panel.name = "Panel"
	panel.theme = Style.make_theme()
	panel.add_theme_stylebox_override("panel", Style.make_texture_panel_style())
	panel.set_anchors_and_offsets_preset(Control.PRESET_CENTER)
	var pw := float(Style.npc("panel_w", 880.0))
	var ph := float(Style.npc("panel_h", 560.0))
	panel.offset_left = -pw * 0.5
	panel.offset_top = -ph * 0.5
	panel.offset_right = pw * 0.5
	panel.offset_bottom = ph * 0.5
	add_child(panel)
	get_viewport().size_changed.connect(_resize_panel)
	_resize_panel()

	var root := VBoxContainer.new()
	root.name = "Root"
	root.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	root.offset_left = 16
	root.offset_top = 16
	root.offset_right = -16
	root.offset_bottom = -16
	root.add_theme_constant_override("separation", Style.spacing("element_gap"))
	panel.add_child(root)

	var header := HBoxContainer.new()
	header.name = "Header"
	root.add_child(header)
	title_label = Label.new()
	title_label.name = "Title"
	title_label.theme = Style.make_theme()
	title_label.add_theme_font_override("font", Style.make_font(Style.font_weight("bold")))
	title_label.add_theme_color_override("font_color", Style.THEME_GOLD)
	title_label.add_theme_font_size_override("font_size", Style.font_size("h2"))
	if _pending_title != "":
		title_label.text = _pending_title
	title_label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	header.add_child(title_label)
	gold_label = Label.new()
	gold_label.name = "Gold"
	gold_label.theme = Style.make_theme()
	gold_label.add_theme_font_override("font", Style.make_mono_font())
	gold_label.add_theme_color_override("font_color", Style.THEME_GOLD)
	gold_label.add_theme_font_size_override("font_size", Style.font_size("label"))
	gold_label.visible = false
	header.add_child(gold_label)
	close_btn = Button.new()
	close_btn.name = "Close"
	close_btn.text = "✕"
	close_btn.focus_mode = Control.FOCUS_ALL
	Style.style_button(close_btn, "body")
	close_btn.custom_minimum_size = Vector2(32, 32)
	close_btn.add_theme_color_override("font_color", Style.COLOR_DIM_TEXT)
	close_btn.pressed.connect(func() -> void: close())
	header.add_child(close_btn)

	body = VBoxContainer.new()
	body.name = "Body"
	body.size_flags_vertical = Control.SIZE_EXPAND_FILL
	body.add_theme_constant_override("separation", Style.spacing("element_gap"))
	var scroll := Style.make_scroll_container()
	scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	root.add_child(scroll)
	body.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	scroll.add_child(body)

	message_label = Label.new()
	message_label.name = "Message"
	message_label.theme = Style.make_theme()
	message_label.add_theme_font_override("font", Style.make_font(Style.font_weight("regular")))
	message_label.add_theme_color_override("font_color", Style.THEME_GRAY_LIGHT)
	message_label.add_theme_font_size_override("font_size", Style.font_size("body"))
	message_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	message_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	root.add_child(message_label)

	_build_body()

## ---- 子类钩子 ----
func _build_body() -> void:
	pass

func _refresh() -> void:
	pass

## ---- 公开接口 ----
func open_panel() -> void:
	var hud := get_node_or_null("/root/HUD")
	if hud != null and hud.backpack_hud != null:
		hud.backpack_hud.hide_tooltip()
	_open = true
	visible = true
	_refresh()
	_set_mouse_released(true)

func close() -> void:
	var hud := get_node_or_null("/root/HUD")
	if hud != null:
		hud.request_inventory_save()
	if _tooltip != null:
		_tooltip.set_pinned(false)
		_tooltip.visible = false
	_open = false
	visible = false
	_set_mouse_released(false)
	closed.emit()

func is_open() -> bool:
	return _open

func set_title(text: String) -> void:
	_pending_title = text
	if title_label != null:
		title_label.text = text

func set_economy(e: RefCounted) -> void:
	economy = e
	if gold_label != null:
		gold_label.visible = e != null
	_refresh_gold()

func show_message(text: String, is_error := false) -> void:
	message_label.text = text
	message_label.add_theme_color_override("font_color",
		Style.THEME_DANGER_RED if is_error else Style.THEME_GRAY_LIGHT)
	_msg_timer = float(Style.npc("msg_ms", 3000)) / 1000.0

func clear_message() -> void:
	message_label.text = ""
	_msg_timer = 0.0

## ---- 常用构建助手 ----
func _make_label(text: String, size_key := "body", color := Color.WHITE) -> Label:
	var l := Label.new()
	l.text = text
	l.theme = Style.make_theme()
	l.add_theme_font_override("font", Style.make_font(Style.font_weight("regular")))
	l.add_theme_color_override("font_color", color)
	l.add_theme_font_size_override("font_size", Style.font_size(size_key))
	l.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	return l

func _make_button(text: String, size_key := "body") -> Button:
	var b := Button.new()
	b.text = text
	b.focus_mode = Control.FOCUS_ALL
	Style.style_button(b, size_key)
	return b

## 分区标题（旧版 .shop-section-title / .enchant-section-title 排版：金色加粗 + 分隔线）
func _make_section_title(text: String) -> Label:
	var l := Label.new()
	l.text = text
	l.add_theme_font_override("font", Style.make_font(Style.font_weight("bold")))
	l.add_theme_color_override("font_color", Style.THEME_GOLD)
	l.add_theme_font_size_override("font_size", Style.font_size("label"))
	l.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return l

## 空态/占位提示（旧版 .shop-empty-hint / .enhance-info-placeholder：灰字居中）
func _make_empty_hint(text: String) -> Label:
	var l := _make_label(text, "body", Style.THEME_GRAY_LIGHT)
	l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	l.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return l

## 物品格（旧版 .inv-cell 排版，含稀有度竖条/图标/徽章/堆叠）
func _make_item_cell(it: Dictionary, min_size := Vector2(120, 52)) -> Node:
	var script: GDScript = load("res://ui/item_cell.gd")
	var c = script.new()
	c.setup(it, min_size)
	c.hovered.connect(func(item: Dictionary) -> void: _show_tooltip(item))
	c.unhovered.connect(func() -> void: _hide_tooltip())
	return c

## 通用格子尺寸（style-config.json npc.cell_*，唯一真源）
func _cell_size(kind := "std") -> Vector2:
	return Vector2(
		float(Style.npc("cell_%s_w" % kind, 120.0)),
		float(Style.npc("cell_%s_h" % kind, 52.0)))

func _show_tooltip(item: Dictionary) -> void:
	if not _open or _tooltip == null or item.is_empty():
		return
	_tooltip.render(item)
	_tooltip.visible = true
	var off := float(Style.npc("tooltip_offset", 16.0))
	_tooltip.position = get_viewport().get_mouse_position() + Vector2(off, off)

func _hide_tooltip() -> void:
	if _tooltip != null and not _tooltip.is_pinned():
		_tooltip.visible = false

## 拖放接收槽（旧版 drag-drop-manager 迁移）
func _make_drop_slot() -> Node:
	var script: GDScript = load("res://ui/drop_slot.gd")
	return script.new()

## 按背包实例定位（拖放数据匹配；找不到返回 -1）
func _find_bp_slot(item: Dictionary) -> int:
	var iid := String(item.get("instance_id", ""))
	for i in _backpack.slots.size():
		var it = _backpack.slots[i]
		if it == null or it.is_empty():
			continue
		if iid != "" and String(it.get("instance_id", "")) == iid:
			return i
		if iid == "" and String(it.get("name", "")) == String(item.get("name", "")) \
				and int(it.get("stack", 1)) >= int(item.get("stack", 1)):
			return i
	return -1

func _make_item_button(item: Dictionary, min_size := Vector2(118, 44)) -> Button:
	var b := Button.new()
	b.focus_mode = Control.FOCUS_ALL
	b.custom_minimum_size = min_size
	var icon := String(item.get("icon_fallback", item.get("icon", "❔")))
	var stack := int(item.get("stack", 1))
	b.text = "%s %s" % [icon, String(item.get("name", "?"))]
	if stack > 1:
		b.text += " x%d" % stack
	Style.style_button(b, "body")
	b.add_theme_color_override("font_color", Style.rarity_color(String(item.get("rarity", "common"))))
	b.add_theme_color_override("font_hover_color", Style.THEME_BG)
	b.add_theme_color_override("font_pressed_color", Style.THEME_BG)
	b.tooltip_text = String(item.get("desc", ""))
	return b

func _refresh_gold() -> void:
	if gold_label == null:
		return
	if economy == null:
		gold_label.visible = false
		return
	gold_label.visible = true
	gold_label.text = "💰 %d" % int(economy.get_gold())

func _set_mouse_released(open_panel: bool) -> void:
	if open_panel:
		_was_captured = Input.mouse_mode == Input.MOUSE_MODE_CAPTURED
		Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	elif _was_captured:
		Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
		_was_captured = false

## Panel escrow is persisted with the same inventory snapshot; full bags never destroy it.
func inventory_state() -> Dictionary:
	var state := {}
	for property in get_property_list():
		var key: String = property.name
		if key in ["_equipped", "_equip", "_equip_src", "_scroll", "_scroll_src", "_sell", "_placed", "_seq", "_carried"]:
			state[key] = get(key)
	return state.duplicate(true)

func restore_inventory_state(state: Dictionary) -> void:
	for key in state:
		set(key, state[key])

func _input(event: InputEvent) -> void:
	if _open and event is InputEventKey and event.pressed and event.keycode == KEY_ESCAPE:
		get_viewport().set_input_as_handled()
		close()

func _resize_panel() -> void:
	var viewport_size := get_viewport().get_visible_rect().size
	var panel_size := Vector2(minf(880, viewport_size.x - 32), minf(640, viewport_size.y - 32))
	panel.offset_left = -panel_size.x / 2
	panel.offset_right = panel_size.x / 2
	panel.offset_top = -panel_size.y / 2
	panel.offset_bottom = panel_size.y / 2
