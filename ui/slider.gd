extends Control
## 滑杆（shadcn slider 的 Godot 翻译）：金 grabber + 深灰轨道 + 数值标签。

signal value_changed(v: float)

const Style := preload("res://ui/style.gd")

var _slider: HSlider
var _value_label: Label
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
	_slider = HSlider.new()
	_slider.custom_minimum_size = Vector2(220, 24)
	_slider.focus_mode = Control.FOCUS_NONE
	var track := Style.make_style(Style.THEME_GRAY_MID, Color(Style.THEME_GRAY_MID, 1.0), 4, 0)
	track.content_margin_top = 3
	track.content_margin_bottom = 3
	var fill := Style.make_style(Style.THEME_GOLD, Color(Style.THEME_GOLD, 1.0), 4, 0)
	fill.content_margin_top = 3
	fill.content_margin_bottom = 3
	var grabber := Style.make_style(Style.THEME_GOLD, Style.THEME_GOLD, 10, 0)
	grabber.content_margin_left = 8
	grabber.content_margin_right = 8
	grabber.content_margin_top = 8
	grabber.content_margin_bottom = 8
	_slider.add_theme_stylebox_override("slider", track)
	_slider.add_theme_stylebox_override("grabber_area", fill)
	_slider.add_theme_stylebox_override("grabber_area_highlight", fill)
	_slider.add_theme_stylebox_override("grabber", grabber)
	_slider.add_theme_constant_override("grabber_offset", 4)
	_slider.value_changed.connect(func(v: float) -> void:
		if _value_label != null:
			_value_label.text = str(int(v))
		value_changed.emit(v))
	h.add_child(_slider)
	_value_label = Label.new()
	_value_label.custom_minimum_size = Vector2(40, 0)
	_value_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	_value_label.add_theme_font_size_override("font_size", Style.font_size("body"))
	_value_label.add_theme_color_override("font_color", Style.THEME_GRAY_LIGHT)
	h.add_child(_value_label)

func setup(minv: float, maxv: float, step: float, value: float) -> void:
	_ensure_built()
	_slider.min_value = minv
	_slider.max_value = maxv
	_slider.step = step
	_slider.value = value
	_value_label.text = str(int(value))

func get_value() -> float:
	_ensure_built()
	return _slider.value
