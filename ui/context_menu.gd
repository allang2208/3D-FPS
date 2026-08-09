extends PopupMenu
## 右键菜单（shadcn context-menu 的 Godot 翻译）：金白主题 PopupMenu。
## 用法：var m := ContextMenu.new(); add_child(m); m.open_at(pos, [{"label":"使用","id":1},{"separator":true},{"label":"丢弃","id":2}])

const Style := preload("res://ui/style.gd")

func _ready() -> void:
	add_theme_stylebox_override("panel", Style.make_panel_style())
	add_theme_color_override("font_color", Style.THEME_WHITE)
	add_theme_color_override("font_hover_color", Color(Style.THEME_BG, 1.0))
	add_theme_color_override("hover_color", Style.THEME_GOLD)
	add_theme_color_override("font_separator_color", Style.THEME_GRAY_MID)
	add_theme_font_size_override("font_size", Style.font_size("body"))

func open_at(pos: Vector2, items: Array) -> void:
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
