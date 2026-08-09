extends Control
## 开关（shadcn switch 的 Godot 翻译）：金色开启 / 灰底关闭。

signal toggled(on: bool)

const Style := preload("res://ui/style.gd")

var _on := false
var _bg: Panel
var _knob: Panel
var _built := false

func _ready() -> void:
	_ensure_built()

func _ensure_built() -> void:
	if _built:
		return
	_built = true
	custom_minimum_size = Vector2(46, 26)
	mouse_filter = Control.MOUSE_FILTER_STOP
	_bg = Panel.new()
	_bg.size = Vector2(46, 26)
	_bg.position = Vector2.ZERO
	var sb := Style.make_style(Style.THEME_GRAY_MID, Color(Style.THEME_GRAY_MID, 1.0), 13, 0)
	_bg.add_theme_stylebox_override("panel", sb)
	_bg.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(_bg)
	_knob = Panel.new()
	_knob.size = Vector2(20, 20)
	var ksb := Style.make_style(Style.THEME_WHITE, Style.THEME_WHITE, 10, 0)
	_knob.add_theme_stylebox_override("panel", ksb)
	_knob.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(_knob)
	gui_input.connect(_on_gui)
	_update()

func _on_gui(event: InputEvent) -> void:
	if event is InputEventMouseButton and event.pressed \
			and event.button_index == MOUSE_BUTTON_LEFT:
		set_on(not _on)

func set_on(v: bool) -> void:
	_ensure_built()
	if _on == v:
		return
	_on = v
	_update()
	toggled.emit(_on)

func is_on() -> bool:
	return _on

func _update() -> void:
	var sb: StyleBoxFlat = _bg.get_theme_stylebox("panel")
	sb.bg_color = Style.THEME_GOLD if _on else Style.THEME_GRAY_MID
	_knob.position = Vector2(4 + (22 if _on else 0), 3)
