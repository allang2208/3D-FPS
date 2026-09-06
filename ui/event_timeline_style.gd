extends RefCounted
## Source adapter: game-style.css 1606–2217 + panel-theme-backpack.css 2195–2266.
## Source timeline's 9/10/11/12px compact text roles are deliberate HUD exceptions.
const Style := preload("res://ui/style.gd")
const LINE := Color("b5cdd92e")
const ACCENT := Color("a2bcc88f")
const TEXT := Color("eef3f5")
const MUTED := Color("9ca8b1")
const DIM := Color("6b7882")
const TRACK := Color("101419")
const WEATHER := Color("45bfff")
const CRITICAL := Color("ff665c")
const WARNING := Color("ffd45c")

static func surface(compact: bool, severity := "") -> StyleBoxTexture:
	var border := "#d56a66" if severity in ["active","critical","evacuation"] else "#c19b63" if severity=="warning" else "#a2bcc88f"
	var result := preload("res://ui/backpack_reference_style.gd").surface("#171d23f2","#080b0ef5",border,8,1)
	result.content_margin_left = 8 if compact else 10
	result.content_margin_right = result.content_margin_left
	result.content_margin_top = 3 if compact else 8
	result.content_margin_bottom = 2 if compact else 9
	return result

static func label(text: String, size_px := 12, heading := false) -> Label:
	var result := Label.new()
	result.text = text
	result.mouse_filter = Control.MOUSE_FILTER_IGNORE
	result.add_theme_font_override("font",Style.make_font(700 if heading else 400))
	result.add_theme_font_size_override("font_size",size_px)
	result.add_theme_color_override("font_color",TEXT)
	return result

static func box(background: Color, border := LINE, radius := 4, padding := 0) -> StyleBoxFlat:
	var result := StyleBoxFlat.new()
	result.bg_color = background
	result.border_color = border
	result.set_border_width_all(1)
	result.set_corner_radius_all(radius)
	result.content_margin_left = padding
	result.content_margin_right = padding
	result.content_margin_top = padding
	result.content_margin_bottom = padding
	return result

static func button(text: String, size_px := 11, control: Button = null) -> Button:
	var result := control if control!=null else Button.new()
	result.text = text
	result.mouse_default_cursor_shape = Control.CURSOR_POINTING_HAND
	result.add_theme_font_override("font",Style.make_font())
	result.add_theme_font_size_override("font_size",size_px)
	result.add_theme_color_override("font_color",MUTED)
	result.add_theme_stylebox_override("normal",box(TRACK,LINE,6,3))
	result.add_theme_stylebox_override("hover",box(Color("232b33"),ACCENT,6,3))
	result.add_theme_stylebox_override("pressed",box(Color("232b33"),ACCENT,6,3))
	result.add_theme_stylebox_override("focus",box(Color.TRANSPARENT,Style.THEME_GOLD,4))
	return result

static func color(event: Dictionary) -> Color:
	if event.get("warning_level","")=="critical": return CRITICAL
	if event.get("warning_level","")=="warning": return WARNING
	if event.get("type","")=="invasion": return Color("ff5b52")
	if event.has("cluster_events"):
		for child in event.cluster_events:
			if child.type=="invasion": return Color("ff5b52")
	return WEATHER if event.get("type","") in ["weather","cluster"] else Color("b9c8d0")

static func icon(event: Dictionary, size_px := 18) -> Control:
	if event.has("icon_path") and ResourceLoader.exists(event.icon_path):
		var image := TextureRect.new()
		image.texture = load(event.icon_path)
		image.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		image.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
		image.custom_minimum_size = Vector2.ONE*size_px
		image.mouse_filter = Control.MOUSE_FILTER_IGNORE
		return image
	var symbol := label(event.get("icon","◆"),size_px)
	symbol.add_theme_font_override("font",Style.make_emoji_font())
	symbol.custom_minimum_size = Vector2.ONE*size_px
	symbol.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	return symbol

static func hover_copy(event: Dictionary) -> String:
	if event.has("cluster_events"):
		return "%s\n%d个事件 · %s\n点击展开完整事件列表" % [event.label,event.cluster_events.size(),event.time_label]
	if event.type=="weather":
		return "%s\n%s · 持续 %s\n%s 至 %s\n%s · 点击查看完整预报" % [event.label,event.intensity_name,event.duration_label,event.starts_at_label,event.ends_at_label,"正在发生" if event.status=="active" else "即将发生"]
	return "%s\n%s · %s\n%s" % [event.label,event.type_label,event.time_label,event.get("detail","当前游标抵达竖线时触发")]
