extends Control
## 复选框（shadcn checkbox 的 Godot 翻译）：小方框 + 勾选图标 + 标签。

signal toggled(on: bool)

const Style := preload("res://ui/style.gd")
const Icons := preload("res://ui/icons.gd")

var _on := false
var _box: Panel
var _check: TextureRect
var _label: Label

func _ready() -> void:
	var h := HBoxContainer.new()
	h.add_theme_constant_override("separation", Style.spacing("element_gap"))
	add_child(h)
	_box = Panel.new()
	_box.custom_minimum_size = Vector2(22, 22)
	var sb := Style.make_style(Style.THEME_GRAY_MID, Style.THEME_GRAY_MID, 4, 1)
	_box.add_theme_stylebox_override("panel", sb)
	h.add_child(_box)
	_check = TextureRect.new()
	_check.custom_minimum_size = Vector2(16, 16)
	_check.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	_check.visible = false
	_box.add_child(_check)
	_check.set_anchors_preset(Control.PRESET_CENTER)
	_label = Label.new()
	_label.add_theme_font_size_override("font_size", Style.font_size("body"))
	_label.add_theme_color_override("font_color", Style.THEME_WHITE)
	h.add_child(_label)
	custom_minimum_size = Vector2(0, 26)
	mouse_filter = Control.MOUSE_FILTER_STOP
	gui_input.connect(_on_gui)

func setup(text: String) -> void:
	_label.text = text

func _on_gui(event: InputEvent) -> void:
	if event is InputEventMouseButton and event.pressed \
			and event.button_index == MOUSE_BUTTON_LEFT:
		set_on(not _on)

func set_on(v: bool) -> void:
	if _on == v:
		return
	_on = v
	_update()
	toggled.emit(_on)

func is_on() -> bool:
	return _on

func _update() -> void:
	_check.visible = _on
	if _on:
		Icons.apply_icon(_check, "check", Style.THEME_BG)
