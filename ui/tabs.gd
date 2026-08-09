extends Control
## 通用分页签（shadcn tabs 的 Godot 翻译）：横向按钮 + 金色下划线指示。
## 用法：var t := Tabs.new(); add_child(t); t.add_tab("设置"); t.tab_changed.connect(...)

signal tab_changed(index: int)

const Style := preload("res://ui/style.gd")

var _tabs: HBoxContainer
var _buttons: Array[Button] = []
var _underline: ColorRect
var _built := false

func _ready() -> void:
	_ensure_built()

func _ensure_built() -> void:
	if _built:
		return
	_built = true
	custom_minimum_size = Vector2(0, 34)
	_tabs = HBoxContainer.new()
	_tabs.add_theme_constant_override("separation", Style.spacing("element_gap"))
	add_child(_tabs)
	_underline = ColorRect.new()
	_underline.color = Style.THEME_GOLD
	_underline.size = Vector2(0, 2)
	_underline.visible = false
	add_child(_underline)

func add_tab(title: String) -> void:
	_ensure_built()
	var idx := _buttons.size()
	var b := Button.new()
	b.text = title
	b.flat = true
	b.focus_mode = Control.FOCUS_NONE
	b.add_theme_font_size_override("font_size", Style.font_size("label"))
	b.add_theme_color_override("font_color", Style.THEME_GRAY_LIGHT)
	b.add_theme_color_override("font_hover_color", Style.THEME_WHITE)
	b.pressed.connect(func() -> void: _select(idx))
	_tabs.add_child(b)
	_buttons.append(b)
	if idx == 0:
		_select(0)

func _select(idx: int) -> void:
	if idx < 0 or idx >= _buttons.size():
		return
	for i in _buttons.size():
		var active := i == idx
		_buttons[i].add_theme_color_override("font_color",
			Style.THEME_GOLD if active else Style.THEME_GRAY_LIGHT)
	var b := _buttons[idx]
	_underline.visible = true
	_underline.position = Vector2(b.global_position.x - global_position.x, b.size.y + 3)
	_underline.size.x = b.size.x
	tab_changed.emit(idx)

func select(index: int) -> void:
	_ensure_built()
	_select(index)

func current() -> int:
	for i in _buttons.size():
		if _buttons[i].get_theme_color("font_color") == Style.THEME_GOLD:
			return i
	return 0
