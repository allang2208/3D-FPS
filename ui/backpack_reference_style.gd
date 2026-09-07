extends RefCounted
## Visual values from the supplied 1912x948 screenshot and game-style.css.
static var _cache := {}
const TOOLTIP_TEXT := Color("#2a2520")
const TOOLTIP_SECONDARY := Color("#4a3f35")
const BADGE_CRAFT := Color("#660033")
const BADGE_ENCHANT := Color("#4a90d9")
const TOOLTIP_ENCHANT_NAME := Color("#c0a060")
const TOOLTIP_SEPARATOR := Color("#00000026")
const ATTRIBUTE_TITLE := Color("#1a1a2e")
const CRAFT_POS := Color("#00ff00")
const CRAFT_NEG := Color("#ff0000")
const RARITY_BADGES := {"common": Color(180.0/255,180.0/255,180.0/255,0.85), "uncommon": Color(122.0/255,200.0/255,122.0/255,0.7), "rare": Color(122.0/255,158.0/255,200.0/255,0.7), "epic": Color(180.0/255,122.0/255,200.0/255,0.7), "mythic": Color(230.0/255,150.0/255,60.0/255,0.78), "legendary": Color(215.0/255,60.0/255,55.0/255,0.8)}

# 用户确认的黑化深青冷钢：空格保持微凸，占用格反向压下。
# 深青只存在于受光面与边缘，避免变成高饱和蓝青主题。
const EQUIP_GLASS_TOP := "#0f2226"
const EQUIP_GLASS_BOTTOM := "#091518"
const EQUIP_GLASS_BORDER := "#31484c"
const EQUIP_EMPTY_TOP := "#173036"
const EQUIP_EMPTY_BOTTOM := "#10262b"
const EQUIP_EMPTY_BORDER := "#28464b"
const EQUIP_HOVER_TOP := "#214249"
const EQUIP_HOVER_BOTTOM := "#17343a"
const EQUIP_HOVER_BORDER := "#789da3"
const EQUIP_EQUIPPED_TOP := "#214249"
const EQUIP_EQUIPPED_BOTTOM := "#0f262b"
const EQUIP_EQUIPPED_BORDER := "#789da3"
const EQUIP_LOCKED_TOP := "#292e30d9"
const EQUIP_LOCKED_BOTTOM := "#1c2224e6"
const EQUIP_LOCKED_BORDER := "#3b4548"
const EQUIP_TEXT := Color("#dce4e3")
const EQUIP_TEXT_MUTED := Color("#849497")
const PANEL_TAB_BG := Color("#2a3238")
const PANEL_TAB_BORDER := Color("#8fa6b1")
const PANEL_DIVIDER := Color("#71828b")
const PANEL_CLOSE_TEXT := Color("#92a3ad")
const PANEL_GLYPH_SHADOW := Color(1, 1, 1, 0.6)

const BACKPACK_EMPTY_TOP := Color("#132d32")
const BACKPACK_EMPTY_BOTTOM := Color("#10262b")
const BACKPACK_EMPTY_LIGHT_EDGE := Color("#31484c")
const BACKPACK_EMPTY_DARK_EDGE := Color("#08191c")
const BACKPACK_EMPTY_HOVER_TOP := Color("#1a3a40")
const BACKPACK_EMPTY_HOVER_BOTTOM := Color("#143136")
const BACKPACK_ITEM_TILE_TOP := Color("#08191c")
const BACKPACK_ITEM_TILE_BOTTOM := Color("#0d2327")
const BACKPACK_ITEM_TOP := Color("#08191cb3")
const BACKPACK_ITEM_BOTTOM := Color("#0d2327b3")
const BACKPACK_ITEM_DARK_EDGE := Color("#051113")
const BACKPACK_ITEM_LIGHT_EDGE := Color("#243a3e")
const BACKPACK_ITEM_HOVER_BOTTOM := Color("#123136cf")
const BACKPACK_DRAG_BOTTOM := Color("#1d464dd6")
const BACKPACK_INVALID_TOP := Color("#39252ad6")
const BACKPACK_INVALID_BOTTOM := Color("#24171ad6")
const BACKPACK_INVALID_DARK_EDGE := Color("#140c0e")
const BACKPACK_INVALID_LIGHT_EDGE := Color("#6a454c")

# Upright glyphs have CSS-sized advances, not a multiline Label's font line height.
class VerticalBadge extends Control:
	var text := "":
		set(value):
			text = value
			queue_redraw()
	var horizontal_alignment := HORIZONTAL_ALIGNMENT_CENTER
	var vertical_alignment := VERTICAL_ALIGNMENT_CENTER
	func _init() -> void:
		clip_contents = true
		mouse_filter = Control.MOUSE_FILTER_IGNORE
		resized.connect(queue_redraw)
	func _draw() -> void:
		if text.is_empty():
			return
		if has_theme_stylebox("normal"):
			draw_style_box(get_theme_stylebox("normal"), Rect2(Vector2.ZERO, size))
		var font := get_theme_font("font")
		var font_size := get_theme_font_size("font_size")
		var chars := text.replace("\n", "")
		var gap := minf(get_theme_constant("line_spacing"), maxf(0, (size.y - chars.length() * font_size) / maxf(1, chars.length() - 1)))
		var advance := font_size + gap
		var y := (size.y - advance * (chars.length() - 1)) / 2.0
		var baseline := (font.get_ascent(font_size) - font.get_descent(font_size)) / 2.0
		for ch in chars:
			var width := font.get_string_size(ch, HORIZONTAL_ALIGNMENT_LEFT, -1, font_size).x
			draw_string(font, Vector2((size.x - width)/2, y + baseline), ch, HORIZONTAL_ALIGNMENT_LEFT, -1, font_size, get_theme_color("font_color"))
			y += advance

# game-style.css: inv/slot-enhanced, -crafted, -enchanted.
static func has_enchantment(item: Dictionary) -> bool:
	var data: Dictionary = item.get("_enchantData", {})
	return bool(item.get("_isEnchanted", false)) or data.get("prefix") != null or data.get("suffix") != null

static func name_right_inset(content: Control, equipment := false) -> int:
	var enchanted := content.get_node_or_null("SourceBadge2") as Control
	var crafted := content.get_node_or_null("SourceBadge1") as Control
	if enchanted != null and enchanted.visible:
		return 38 if equipment else 28
	if crafted != null and crafted.visible:
		return 20 if equipment else 16
	return 8 if equipment else 4

static func item_shadow(label: Label, light := false) -> void:
	label.add_theme_color_override("font_shadow_color", Color(1, 1, 1, 0.7) if light else Color(0, 0, 0, 0.7))
	label.add_theme_constant_override("shadow_offset_x", 0)
	label.add_theme_constant_override("shadow_offset_y", 1)
	label.add_theme_constant_override("shadow_outline_size", 1)

static func update_item_badges(content: Control, item: Dictionary, equipment := false) -> void:
	var crafted: bool = bool(item.get("_isCrafted", false)) or not item.get("_craftData", {}).is_empty()
	for value in item.get("gunsmith_parts", {}).values():
		crafted = crafted or not str(value).is_empty()
	var flags := [int(item.get("enhanceLevel", 0)) > 0, crafted, has_enchantment(item)]
	var texts := ["已强化", "已改造", "已附魔"]
	for i in 3:
		var badge := content.get_node_or_null("SourceBadge%d" % i) as VerticalBadge
		if badge == null:
			badge = VerticalBadge.new()
			badge.name = "SourceBadge%d" % i
			badge.text = "\n".join(texts[i].split(""))
			badge.mouse_filter = Control.MOUSE_FILTER_IGNORE
			badge.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
			badge.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
			badge.add_theme_font_size_override("font_size", 10 if equipment else 8)
			badge.add_theme_font_override("font", preload("res://ui/style.gd").make_font(700))
			badge.add_theme_constant_override("line_spacing", 2 if equipment and i == 0 else 0)
			badge.anchor_bottom = 1.0
			badge.offset_top = 0
			var width := 14 if equipment else 10
			if i == 0:
				badge.offset_left = 21 if equipment else 14
				badge.offset_right = badge.offset_left + width
			else:
				badge.anchor_left = 1.0
				badge.anchor_right = 1.0
				badge.offset_right = -2 if i == 1 else (-20 if equipment else -14)
				badge.offset_left = badge.offset_right - width
			var tops := ["#ffd700", "#660033", "#4a90d9"]
			var bottoms := ["#ffaa00", "#660033", "#4a90d9"]
			badge.add_theme_stylebox_override("normal", surface(tops[i], bottoms[i], tops[i], 3 if equipment else 2, 0, 0, i == 0))
			badge.add_theme_color_override("font_color", Color("#1a1a2e") if i == 0 else Color.WHITE)
			content.add_child(badge)
		badge.visible = flags[i]

static func hide_item_badges(content: Control) -> void:
	for i in 3:
		var badge := content.get_node_or_null("SourceBadge%d" % i) as Control
		if badge != null:
			badge.visible = false
static func surface(top: String, bottom: String, border: String, radius := 8, width := 2, padding := 0, diagonal := false) -> StyleBoxTexture:
	var key := str([top, bottom, border, radius, width, diagonal])
	if not _cache.has(key):
		var img := Image.create(128, 128, false, Image.FORMAT_RGBA8)
		for y in 128:
			for x in 128:
				var point := Vector2(x + 0.5, y + 0.5)
				var center := point.clamp(Vector2.ONE * radius, Vector2.ONE * (128 - radius))
				var distance := point.distance_to(center)
				var weight: float = (x + y) / 254.0 if diagonal else y / 127.0
				var color := Color(top).lerp(Color(bottom), weight)
				if x < width or y < width or x >= 128-width or y >= 128-width or distance > radius-width:
					color = Color(border)
				color.a *= 1.0 if radius == 0 else clampf(radius + 0.5 - distance, 0, 1)
				img.set_pixel(x, y, color)
		_cache[key] = ImageTexture.create_from_image(img)
	var box := StyleBoxTexture.new()
	box.texture = _cache[key]
	for edge in [SIDE_LEFT, SIDE_TOP, SIDE_RIGHT, SIDE_BOTTOM]:
		box.set_texture_margin(edge, radius)
		box.set_content_margin(edge, padding)
	return box

static func slot_surface(fill_top: Color, fill_bottom: Color, top_left_edge: Color, bottom_right_edge: Color) -> StyleBoxTexture:
	var key := str(["slot", fill_top, fill_bottom, top_left_edge, bottom_right_edge])
	if not _cache.has(key):
		var img := Image.create(128, 128, false, Image.FORMAT_RGBA8)
		for y in 128:
			for x in 128:
				var color := fill_top.lerp(fill_bottom, y / 127.0)
				# 单像素低对比边缘避免相邻槽位拼成双重粗分割线。
				if x < 1 or y < 1:
					color = top_left_edge
				elif x >= 127 or y >= 127:
					color = bottom_right_edge
				img.set_pixel(x, y, color)
		_cache[key] = ImageTexture.create_from_image(img)
	var box := StyleBoxTexture.new()
	box.texture = _cache[key]
	for edge in [SIDE_LEFT, SIDE_TOP, SIDE_RIGHT, SIDE_BOTTOM]:
		box.set_texture_margin(edge, 1)
	return box

static func clear_cache() -> void:
	_cache.clear()

# Source .two-handed-locked .slot-icon: grayscale(100%); opacity is applied by the slot.
static var _locked_icon: ShaderMaterial
static func locked_icon_material() -> ShaderMaterial:
	if _locked_icon == null:
		var shader := Shader.new()
		shader.code = "shader_type canvas_item; void fragment() { vec4 c = texture(TEXTURE, UV) * COLOR; float gray = dot(c.rgb, vec3(0.2126, 0.7152, 0.0722)); COLOR = vec4(vec3(gray), c.a); }"
		_locked_icon = ShaderMaterial.new()
		_locked_icon.shader = shader
	return _locked_icon
