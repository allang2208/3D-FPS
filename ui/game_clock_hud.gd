extends PanelContainer
const Style = preload("res://ui/style.gd")
var clock: RefCounted
var text: Label
var icon: Label
var dial: Control

func _ready() -> void:
	name = "GameClock"
	theme = Style.make_theme()
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	custom_minimum_size = Vector2(286, 74)
	add_theme_stylebox_override("panel", Style.make_hud_surface(12, 6))
	var row := HBoxContainer.new()
	row.alignment = BoxContainer.ALIGNMENT_BEGIN
	row.add_theme_constant_override("separation", 10)
	row.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(row)
	dial = SunDial.new()
	row.add_child(dial)
	icon = Label.new()
	icon.add_theme_font_override("font", Style.make_emoji_font())
	icon.add_theme_font_size_override("font_size", 14)
	row.add_child(icon)
	text = Label.new()
	Style.apply_text_role(text, &"body")
	text.add_theme_color_override("font_color", Style.COLOR_HUD_TEXT)
	text.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	row.add_child(text)
	get_viewport().size_changed.connect(resize_clock)
	resize_clock()

func resize_clock() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_TOP_RIGHT)
	offset_left = -398
	offset_right = -112
	offset_top = 12
	offset_bottom = 86

func _process(_delta: float) -> void:
	if clock == null: return
	var value: Dictionary = clock.model()
	text.text = "第%d日 · %02d:%02d · %s" % [value.day, value.hour, value.minute, value.period]
	icon.text = value.icon
	dial.phase = value.phase
	dial.queue_redraw()

class SunDial extends Control:
	var phase := 0.25
	func _ready() -> void:
		custom_minimum_size = Vector2(60, 60)
		mouse_filter = Control.MOUSE_FILTER_IGNORE
	func _draw() -> void:
		var center := Vector2(30, 30)
		draw_circle(center, 27.5, Color("#080c10e0"))
		draw_arc(center, 27.5, 0, TAU, 72, Color("#a2bcc88f"), 1.875, true)
		draw_arc(center, 25, PI, TAU, 36, Color("#c6b477"), 3.125, true)
		draw_arc(center, 25, 0, PI, 36, Color("#66829a"), 3.125, true)
		draw_line(Vector2(5, 30), Vector2(55, 30), Color("#c4d3da61"), 1, true)
		for i in 24:
			var direction := Vector2.from_angle(i * TAU / 24.0 - PI / 2)
			var major := i % 6 == 0
			draw_line(center + direction * (20 if major else 24.375), center + direction * 26.875, Color("#c4d3da") if major else Color("#c4d3da61"), 2 if major else 1.25, true)
		var tip := center + Vector2.from_angle(phase * TAU - PI) * 18.75
		draw_line(center, tip, Color("#f3f6f8"), 2.75, true)
		draw_circle(tip, 3.75, Color("#c4d3da"))
		draw_circle(center, 2.5, Color("#c4d3da"))
