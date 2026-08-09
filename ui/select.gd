extends Control
## 下拉选择行（shadcn select 的 Godot 翻译）：标签 + OptionButton。

signal item_selected(index: int)

const Style := preload("res://ui/style.gd")

var _option: OptionButton
var _label: Label

func _ready() -> void:
	var h := HBoxContainer.new()
	h.add_theme_constant_override("separation", Style.spacing("element_gap"))
	add_child(h)
	_label = Label.new()
	_label.custom_minimum_size = Vector2(110, 0)
	_label.add_theme_font_size_override("font_size", Style.font_size("body"))
	_label.add_theme_color_override("font_color", Style.THEME_GRAY_LIGHT)
	h.add_child(_label)
	_option = OptionButton.new()
	_option.custom_minimum_size = Vector2(220, 30)
	_option.add_theme_stylebox_override("normal",
		Style.make_style(Style.THEME_BG, Style.THEME_GRAY_MID, 4, 1))
	_option.add_theme_stylebox_override("hover",
		Style.make_style(Color(Style.THEME_GRAY_MID, 0.7), Style.THEME_GRAY_MID, 4, 1))
	_option.add_theme_stylebox_override("pressed",
		Style.make_style(Color(Style.THEME_GOLD, 0.25), Style.THEME_GOLD, 4, 1))
	_option.add_theme_color_override("font_color", Style.THEME_WHITE)
	_option.add_theme_color_override("font_hover_color", Style.THEME_GOLD)
	_option.add_theme_font_size_override("font_size", Style.font_size("body"))
	_option.item_selected.connect(func(i: int) -> void: item_selected.emit(i))
	h.add_child(_option)

func setup(text: String) -> void:
	_label.text = text

func add_item(item_text: String, id := -1) -> void:
	_option.add_item(item_text, id)

func select(index: int) -> void:
	_option.select(index)

func get_selected_id() -> int:
	return _option.get_selected_id()

func get_selected_index() -> int:
	return _option.selected
