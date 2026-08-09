extends VBoxContainer
## 主菜单导航（shadcn navigation-menu 简化版）：竖排大按钮 + 可选图标。

signal item_activated(index: int)

const Style := preload("res://ui/style.gd")
const Icons := preload("res://ui/icons.gd")
var _built := false

func _ready() -> void:
	_ensure_built()

func _ensure_built() -> void:
	if _built:
		return
	_built = true
	add_theme_constant_override("separation", Style.spacing("element_gap"))

func add_item(title: String, icon := "") -> void:
	_ensure_built()
	var idx := get_child_count()
	var b := Button.new()
	b.text = title
	b.alignment = HORIZONTAL_ALIGNMENT_LEFT
	b.custom_minimum_size = Vector2(280, 46)
	Style.style_button(b, "label")
	b.add_theme_font_size_override("font_size", Style.font_size("h2"))
	b.add_theme_color_override("font_color", Style.THEME_WHITE)
	b.add_theme_color_override("font_hover_color", Color(Style.THEME_BG, 1.0))
	if not icon.is_empty():
		b.icon = Icons.get_icon(icon)
		b.icon_alignment = HORIZONTAL_ALIGNMENT_LEFT
		b.add_theme_constant_override("icon_max_width", 28)
		b.add_theme_color_override("icon_normal_color", Style.THEME_GOLD)
		b.add_theme_color_override("icon_hover_color", Style.THEME_BG)
	b.pressed.connect(func() -> void: item_activated.emit(idx))
	add_child(b)
