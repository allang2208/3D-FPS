extends Panel
## 物品格（复刻旧版 .inv-cell 排版）：稀有度竖标签 + 图标 + 名称 + 堆叠数 + 强化/改造/附魔徽章。
## 面板里调用：var c := _make_item_cell(it, Vector2(120, 52)); c.pressed.connect(...)

const Style := preload("res://ui/style.gd")

signal pressed(cell: Panel)
signal hovered(item: Dictionary)

var item := {}

var _rarity_bar: ColorRect
var _rarity_lbl: Label
var _icon: TextureRect
var _icon_fallback: Label
var _name_lbl: Label
var _stack_lbl: Label
var _badges: HBoxContainer
var _price_lbl: Label

func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_STOP
	mouse_entered.connect(func() -> void: hovered.emit(item))
	gui_input.connect(_on_gui_input)

func setup(it: Dictionary, min_size := Vector2(120, 52)) -> void:
	item = it
	custom_minimum_size = min_size
	_build()

func _build() -> void:
	for c in get_children():
		c.queue_free()
	var rarity := String(item.get("rarity", "common"))
	add_theme_stylebox_override("panel", Style.make_slot_style(
		Style.COLOR_SLOT_BG, Style.rarity_color(rarity), "sm", 1))

	# 稀有度竖条（左缘，色带 + 竖排文字，旧版 writing-mode: vertical-rl）
	_rarity_bar = ColorRect.new()
	_rarity_bar.color = Style.rarity_color(rarity)
	_rarity_bar.set_anchors_and_offsets_preset(Control.PRESET_LEFT_WIDE)
	_rarity_bar.offset_right = 6
	_rarity_bar.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(_rarity_bar)
	_rarity_lbl = Label.new()
	_rarity_lbl.text = Style.rarity_label(rarity)
	_rarity_lbl.rotation = -PI / 2.0
	_rarity_lbl.pivot_offset = Vector2(6, 6)
	_rarity_lbl.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_LEFT)
	_rarity_lbl.offset_left = 0
	_rarity_lbl.offset_bottom = -6
	_rarity_lbl.add_theme_font_size_override("font_size", 8)
	_rarity_lbl.add_theme_font_override("font", Style.make_font(Style.font_weight("bold")))
	_rarity_lbl.add_theme_color_override("font_color", Style.COLOR_BLACK)
	_rarity_lbl.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(_rarity_lbl)

	# 图标（图片优先，fallback emoji）
	var icon_path := String(item.get("icon", ""))
	_icon = TextureRect.new()
	_icon.custom_minimum_size = Vector2(30, 30)
	_icon.position = Vector2(12, 6)
	_icon.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	_icon.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	_icon.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var tex := load(icon_path) if icon_path != "" and ResourceLoader.exists(icon_path) else null
	_icon.texture = tex if tex is Texture2D else null
	add_child(_icon)
	var fallback := String(item.get("icon_fallback", ""))
	_icon_fallback = Label.new()
	_icon_fallback.text = fallback if fallback != "" else "❔"
	_icon_fallback.position = Vector2(14, 4)
	_icon_fallback.add_theme_font_size_override("font_size", 24)
	_icon_fallback.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_icon_fallback.visible = _icon.texture == null
	add_child(_icon_fallback)

	# 名称（右下）
	_name_lbl = Label.new()
	_name_lbl.text = String(item.get("name", "?"))
	_name_lbl.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_LEFT)
	_name_lbl.offset_left = 48
	_name_lbl.offset_bottom = -16
	_name_lbl.add_theme_font_size_override("font_size", 11)
	_name_lbl.add_theme_font_override("font", Style.make_font(Style.font_weight("bold")))
	_name_lbl.add_theme_color_override("font_color", Style.COLOR_WHITE)
	_name_lbl.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(_name_lbl)

	# 堆叠数（右下角，旧版 .inv-stack）
	var stack := int(item.get("stack", 1))
	if stack > 1:
		_stack_lbl = Label.new()
		_stack_lbl.text = "x%d" % stack
		_stack_lbl.add_theme_font_size_override("font_size", 11)
		_stack_lbl.add_theme_font_override("font", Style.make_mono_font(600))
		_stack_lbl.add_theme_color_override("font_color", Style.COLOR_BLACK)
		_stack_lbl.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_RIGHT)
		_stack_lbl.offset_left = -34
		_stack_lbl.offset_bottom = -2
		_stack_lbl.mouse_filter = Control.MOUSE_FILTER_IGNORE
		add_child(_stack_lbl)

	# 价格角标（商店/出售格，旧版 .shop-buy-cell-price 右上角）
	var price := int(item.get("_price", 0))
	if price > 0:
		_price_lbl = Label.new()
		_price_lbl.text = "💰%d" % price
		_price_lbl.set_anchors_and_offsets_preset(Control.PRESET_TOP_RIGHT)
		_price_lbl.offset_left = -60
		_price_lbl.offset_top = 1
		_price_lbl.add_theme_font_size_override("font_size", 10)
		_price_lbl.add_theme_font_override("font", Style.make_font(Style.font_weight("bold")))
		_price_lbl.add_theme_color_override("font_color", Style.THEME_GOLD)
		_price_lbl.mouse_filter = Control.MOUSE_FILTER_IGNORE
		add_child(_price_lbl)

	# 徽章（已强化 / 已改造 / 已附魔，顶部横排，旧版 inv-enhanced/crafted/enchanted）
	_badges = HBoxContainer.new()
	_badges.set_anchors_and_offsets_preset(Control.PRESET_TOP_LEFT)
	_badges.offset_left = 42
	_badges.offset_top = 2
	_badges.add_theme_constant_override("separation", 2)
	_badges.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(_badges)
	var enhance := int(item.get("enhanceLevel", 0))
	if enhance > 0:
		_badges.add_child(_make_badge("已强化+%d" % enhance, Style.COLOR_BADGE_GOLD_BG, Style.COLOR_BADGE_GOLD_TEXT))
	if not (item.get("_craftData", {}) as Dictionary).is_empty():
		_badges.add_child(_make_badge("已改造", Style.COLOR_BADGE_CRAFT_BG, Style.COLOR_BADGE_CRAFT_TEXT))
	if bool(item.get("_isEnchanted", false)):
		_badges.add_child(_make_badge("已附魔", Style.COLOR_BADGE_ENCHANT_BG, Style.COLOR_BADGE_ENCHANT_TEXT))

func _make_badge(text: String, bg: Color, fg: Color) -> Label:
	var l := Label.new()
	l.text = text
	l.add_theme_font_size_override("font_size", 8)
	l.add_theme_font_override("font", Style.make_font(Style.font_weight("bold")))
	l.add_theme_color_override("font_color", fg)
	l.add_theme_stylebox_override("normal", Style.make_style(bg, Color(0, 0, 0, 0), 2, 0))
	l.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return l

func _on_gui_input(event: InputEvent) -> void:
	if event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_LEFT:
		pressed.emit(self)

func set_item(it: Dictionary) -> void:
	item = it
	_build()

func set_price(v: int) -> void:
	item["_price"] = v
	if _price_lbl != null:
		_price_lbl.text = "💰%d" % v
