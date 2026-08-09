extends PopupMenu
## 右键菜单（shadcn context-menu 的 Godot 翻译）：金白主题 PopupMenu。
## 用法：var m := ContextMenu.new(); add_child(m); m.open_at(pos, [{"label":"使用","id":1},{"separator":true},{"label":"丢弃","id":2}])

const Style := preload("res://ui/style.gd")
var _built := false

func _ready() -> void:
	_ensure_built()

func _ensure_built() -> void:
	if _built:
		return
	_built = true
	# 信息浮层统一白底（与物品浮窗一致，纸质卡片感）
	var sb := Style.make_style(Style.COLOR_TT_BG, Style.COLOR_TT_BORDER, Style.RADIUS_MD, 1)
	sb.shadow_color = Style.COLOR_TT_SHADOW
	sb.shadow_size = 12
	sb.shadow_offset = Vector2(0, 4)
	add_theme_stylebox_override("panel", sb)
	add_theme_color_override("font_color", Style.COLOR_TT_NAME)
	add_theme_color_override("font_hover_color", Color(Style.THEME_BG, 1.0))
	add_theme_color_override("hover_color", Style.THEME_GOLD)
	add_theme_color_override("font_separator_color", Style.COLOR_TT_SECTION_BORDER)
	add_theme_font_size_override("font_size", Style.font_size("body"))

func open_at(pos: Vector2, items: Array) -> void:
	_ensure_built()
	clear()
	for it in items:
		if it is Dictionary:
			if it.get("separator", false):
				add_separator()
			else:
				add_item(str(it.get("label", "?")), int(it.get("id", -1)))
		else:
			add_item(str(it))
	position = pos
	popup()
