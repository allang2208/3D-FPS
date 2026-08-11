extends PanelContainer
## 左侧竖排导航（参考图：技能配置/天赋树界面的左侧导航模块）
## 纯文字按钮 + 选中亮底加粗；整体深色 HUD 模块风格（COLOR_HUD_*）
## 用法：left_nav.setup([["status","角色"],["equip","背包"],...])；item_activated(id) 信号

signal item_activated(id: String)

const Style := preload("res://ui/style.gd")

var _buttons := {}
var _selected := ""


func _ready() -> void:
	add_theme_stylebox_override("panel",
		Style.make_style(Color(Style.COLOR_HUD_BG, 0.72), Color(Style.COLOR_HUD_BORDER, 0.6), 8, 1))


func setup(items: Array) -> void:
	for it in items:
		var id := String(it[0])
		var b := Button.new()
		b.text = String(it[1])
		b.alignment = HORIZONTAL_ALIGNMENT_LEFT
		b.custom_minimum_size = Vector2(150, 30)
		b.focus_mode = Control.FOCUS_NONE
		b.mouse_filter = Control.MOUSE_FILTER_STOP
		b.add_theme_font_size_override("font_size", 12)
		b.add_theme_color_override("font_hover_color", Style.COLOR_HUD_GOLD)
		_update_style(b, false)
		b.pressed.connect(func() -> void:
			select(id)
			item_activated.emit(id))
		add_child(b)
		_buttons[id] = b
	if not _selected.is_empty():
		select(_selected)


func select(id: String) -> void:
	if not _buttons.has(id):
		return
	_selected = id
	for key in _buttons:
		_update_style(_buttons[key], key == id)


func _update_style(b: Button, active: bool) -> void:
	if active:
		b.add_theme_stylebox_override("normal",
			Style.make_style(Color(Style.COLOR_HUD_TEXT, 0.14), Color(Style.COLOR_HUD_GOLD, 0.8), 5, 1))
		b.add_theme_stylebox_override("hover", b.get_theme_stylebox("normal"))
		b.add_theme_font_override("font", Style.make_font(700))
		b.add_theme_color_override("font_color", Style.COLOR_HUD_GOLD)
	else:
		b.add_theme_stylebox_override("normal",
			Style.make_style(Style.COLOR_TRANSPARENT, Style.COLOR_TRANSPARENT, 0, 0))
		b.add_theme_stylebox_override("hover",
			Style.make_style(Color(Style.COLOR_HUD_TEXT, 0.10), Style.COLOR_TRANSPARENT, 5, 0))
		b.add_theme_font_override("font", Style.make_font(400))
		b.add_theme_color_override("font_color", Style.COLOR_HUD_TEXT)
