extends Control
## 文本输入行（shadcn input 的 Godot 翻译）：标签 + LineEdit。

signal text_submitted(text: String)

const Style := preload("res://ui/style.gd")

var _line: LineEdit
var _label: Label
var _built := false

func _ready() -> void:
	_ensure_built()

func _ensure_built() -> void:
	if _built:
		return
	_built = true
	var h := HBoxContainer.new()
	h.add_theme_constant_override("separation", Style.spacing("element_gap"))
	add_child(h)
	_label = Label.new()
	_label.custom_minimum_size = Vector2(110, 0)
	_label.add_theme_font_size_override("font_size", Style.font_size("body"))
	_label.add_theme_color_override("font_color", Style.THEME_GRAY_LIGHT)
	h.add_child(_label)
	_line = LineEdit.new()
	_line.custom_minimum_size = Vector2(220, 30)
	_line.add_theme_stylebox_override("normal",
		Style.make_style(Style.THEME_BG, Style.THEME_GRAY_MID, Style.RADIUS_SM, 1))
	_line.add_theme_stylebox_override("focus",
		Style.make_style(Style.THEME_BG, Style.THEME_GOLD, Style.RADIUS_SM, 1))
	_line.add_theme_color_override("font_color", Style.THEME_WHITE)
	_line.add_theme_color_override("font_placeholder_color", Style.THEME_GRAY_MID)
	_line.add_theme_font_size_override("font_size", Style.font_size("body"))
	_line.text_submitted.connect(func(t: String) -> void: text_submitted.emit(t))
	h.add_child(_line)

func setup(text: String, placeholder := "") -> void:
	_ensure_built()
	_label.text = text
	_line.placeholder_text = placeholder

func get_text() -> String:
	_ensure_built()
	return _line.text

func set_text(v: String) -> void:
	_ensure_built()
	_line.text = v
