extends PanelContainer
## 物品浮窗（复刻旧版 equip-tooltip：白底圆角、图标+名称+类型+稀有度+属性+描述）
## 行为由 backpack_hud 驱动：悬停跟随、点击固定、贴边翻转、关闭按钮。

const Style := preload("res://ui/style.gd")

signal close_requested

var _pinned := false
var _icon: TextureRect
var _name_label: Label
var _type_row: HBoxContainer
var _stats_box: VBoxContainer
var _extra_box: VBoxContainer
var _desc_label: Label
var _close_btn: Button

func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	theme = Style.make_theme()
	add_theme_stylebox_override("panel", Style.make_style(Style.COLOR_TT_BG, Style.COLOR_TT_BORDER, 8, 2))
	_build()
	custom_minimum_size = Vector2(300, 0)

func _build() -> void:
	var margin := MarginContainer.new()
	margin.mouse_filter = Control.MOUSE_FILTER_IGNORE
	margin.add_theme_constant_override("margin_left", 12)
	margin.add_theme_constant_override("margin_right", 12)
	margin.add_theme_constant_override("margin_top", 10)
	margin.add_theme_constant_override("margin_bottom", 10)
	add_child(margin)
	var vbox := VBoxContainer.new()
	vbox.add_theme_constant_override("separation", 6)
	margin.add_child(vbox)
	# 头部：图标 + 名称/类型 + 关闭按钮
	var header := HBoxContainer.new()
	header.add_theme_constant_override("separation", 10)
	vbox.add_child(header)
	_icon = TextureRect.new()
	_icon.custom_minimum_size = Vector2(42, 42)
	_icon.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	_icon.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	_icon.mouse_filter = Control.MOUSE_FILTER_IGNORE
	header.add_child(_icon)
	var title_box := VBoxContainer.new()
	title_box.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	title_box.add_theme_constant_override("separation", 2)
	header.add_child(title_box)
	_name_label = Label.new()
	_name_label.add_theme_font_size_override("font_size", 17)
	_name_label.add_theme_color_override("font_color", Style.COLOR_TT_NAME)
	title_box.add_child(_name_label)
	_type_row = HBoxContainer.new()
	_type_row.add_theme_constant_override("separation", 4)
	title_box.add_child(_type_row)
	_close_btn = Button.new()
	_close_btn.text = "✕"
	_close_btn.custom_minimum_size = Vector2(24, 24)
	_close_btn.flat = false
	_close_btn.add_theme_stylebox_override("normal", Style.make_style(Style.COLOR_TT_CLOSE_BG, Color(0, 0, 0, 0.0), 12, 0))
	_close_btn.add_theme_stylebox_override("hover", Style.make_style(Style.COLOR_TT_CLOSE_HOVER, Color(0, 0, 0, 0.0), 12, 0))
	_close_btn.add_theme_stylebox_override("pressed", Style.make_style(Style.COLOR_TT_CLOSE_HOVER, Color(0, 0, 0, 0.0), 12, 0))
	_close_btn.add_theme_color_override("font_color", Color.WHITE)
	_close_btn.add_theme_font_size_override("font_size", 13)
	_close_btn.pressed.connect(func() -> void: close_requested.emit())
	header.add_child(_close_btn)
	# 属性
	_stats_box = VBoxContainer.new()
	_stats_box.add_theme_constant_override("separation", 3)
	vbox.add_child(_stats_box)
	# 额外信息
	_extra_box = VBoxContainer.new()
	_extra_box.add_theme_constant_override("separation", 3)
	vbox.add_child(_extra_box)
	# 描述
	_desc_label = Label.new()
	_desc_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_desc_label.add_theme_font_size_override("font_size", 12)
	_desc_label.add_theme_color_override("font_color", Style.COLOR_TT_DESC)
	vbox.add_child(_desc_label)

func render(item: Dictionary) -> void:
	if item.is_empty():
		return
	var icon_path := String(item.get("icon", ""))
	if icon_path != "":
		var tex := load(icon_path)
		_icon.texture = tex if tex is Texture2D else null
	else:
		_icon.texture = null
	_name_label.text = String(item.get("name", ""))
	var enhance: int = item.get("enhanceLevel", 0)
	if enhance > 0:
		_name_label.text += "  已强化 +%d" % enhance
	# 类型 | 稀有度 | Lv
	for child in _type_row.get_children():
		child.queue_free()
	var type_text := String(item.get("type", "物品"))
	var type_lbl := Label.new()
	type_lbl.text = type_text
	type_lbl.add_theme_font_size_override("font_size", 12)
	type_lbl.add_theme_color_override("font_color", Style.COLOR_TT_TYPE)
	_type_row.add_child(type_lbl)
	var rarity_key := String(item.get("rarity", "common"))
	var rarity_lbl := Label.new()
	rarity_lbl.text = "| " + Style.rarity_label(rarity_key)
	rarity_lbl.add_theme_font_size_override("font_size", 12)
	rarity_lbl.add_theme_color_override("font_color", Style.rarity_color(rarity_key))
	var ls := LabelSettings.new()
	ls.font_size = 12
	ls.font_color = Style.rarity_color(rarity_key)
	ls.outline_size = 2
	ls.outline_color = Color.BLACK
	rarity_lbl.label_settings = ls
	_type_row.add_child(rarity_lbl)
	var level: int = item.get("level", 0)
	if level > 0:
		var lv_lbl := Label.new()
		lv_lbl.text = "| Lv.%d" % level
		lv_lbl.add_theme_font_size_override("font_size", 12)
		lv_lbl.add_theme_color_override("font_color", Style.COLOR_TT_TYPE)
		_type_row.add_child(lv_lbl)
	# 属性行
	_clear_children(_stats_box)
	var stats: Array = item.get("stats", [])
	for s in stats:
		var name := String(s.get("name", ""))
		if name == "":
			continue
		_stats_box.add_child(_make_row(name, String(s.get("value", "")), bool(s.get("pos", false))))
	# 额外行
	_clear_children(_extra_box)
	var category := String(item.get("category", ""))
	if category != "":
		_extra_box.add_child(_make_row("分类", category, false))
	var stack: int = item.get("stack", 1)
	var stack_max: int = item.get("stack_max", 99)
	_extra_box.add_child(_make_row("堆叠", "%d/%d" % [stack, stack_max], false))
	# 描述
	_desc_label.text = String(item.get("desc", ""))

func is_pinned() -> bool:
	return _pinned

func set_pinned(v: bool) -> void:
	_pinned = v
	mouse_filter = Control.MOUSE_FILTER_STOP if v else Control.MOUSE_FILTER_IGNORE
	_close_btn.visible = true

func _make_row(name: String, value: String, pos: bool) -> HBoxContainer:
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 12)
	var name_lbl := Label.new()
	name_lbl.text = name
	name_lbl.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	name_lbl.add_theme_font_size_override("font_size", 12)
	name_lbl.add_theme_color_override("font_color", Style.COLOR_TT_TYPE)
	row.add_child(name_lbl)
	var val_lbl := Label.new()
	val_lbl.text = value
	val_lbl.add_theme_font_size_override("font_size", 12)
	val_lbl.add_theme_color_override("font_color", Style.COLOR_TT_POS if pos else Style.COLOR_TT_VAL)
	row.add_child(val_lbl)
	return row

func _clear_children(box: Node) -> void:
	for child in box.get_children():
		child.queue_free()
