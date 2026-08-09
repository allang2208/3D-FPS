extends Control
## 开关（shadcn switch 的 Godot 翻译）：金色开启 / 灰底关闭。

signal toggled(on: bool)

const Style := preload("res://ui/style.gd")

var _on := false
var _bg: ColorRect
var _knob: ColorRect
var _built := false

func _ready() -> void:
	_ensure_built()

func _ensure_built() -> void:
	if _built:
		return
	_built = true
	custom_minimum_size = Vector2(46, 26)
	mouse_filter = Control.MOUSE_FILTER_STOP
	_bg = ColorRect.new()
	_bg.size = Vector2(46, 26)
	_bg.position = Vector2.ZERO
	_bg.color = Style.THEME_GRAY_MID
	_bg.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(_bg)
	_knob = ColorRect.new()
	_knob.size = Vector2(20, 20)
	_knob.color = Style.THEME_WHITE
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
	_bg.color = Style.THEME_GOLD if _on else Style.THEME_GRAY_MID
	_knob.position = Vector2(4 + (22 if _on else 0), 3)
