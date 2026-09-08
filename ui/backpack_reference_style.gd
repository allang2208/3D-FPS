extends RefCounted
## Visual values from the supplied 1912x948 screenshot and game-style.css.
static var _cache := {}
const TOOLTIP_TEXT := Color("#dce2e6")
const TOOLTIP_SECONDARY := Color("#b5c0c8")
const BADGE_CRAFT := Color("#660033")
const BADGE_ENCHANT := Color("#4a90d9")
const TOOLTIP_ENCHANT_NAME := Color("#c0a060")
const TOOLTIP_SEPARATOR := Color("#dceaf033")
const ATTRIBUTE_TITLE := Color("#dce2e6")
const CRAFT_POS := Color("#68d5ad")
const CRAFT_NEG := Color("#ff8193")
const RARITY_BADGES := {"common": Color(180.0/255,180.0/255,180.0/255,0.85), "uncommon": Color(122.0/255,200.0/255,122.0/255,0.7), "rare": Color(122.0/255,158.0/255,200.0/255,0.7), "epic": Color(180.0/255,122.0/255,200.0/255,0.7), "mythic": Color(230.0/255,150.0/255,60.0/255,0.78), "legendary": Color(215.0/255,60.0/255,55.0/255,0.8)}

# 2026-09-07 approved clock/timeline charcoal direction: quiet, flat interiors.
const EQUIP_GLASS_TOP := "#0d1115"
const EQUIP_GLASS_BOTTOM := "#080b0e"
const EQUIP_GLASS_BORDER := "#272f35"
const EQUIP_EMPTY_TOP := "#101419"
const EQUIP_EMPTY_BOTTOM := "#0b0e12"
const EQUIP_EMPTY_BORDER := "#242a30"
const EQUIP_HOVER_TOP := "#1b2229"
const EQUIP_HOVER_BOTTOM := "#12181e"
const EQUIP_HOVER_BORDER := "#71828d"
const EQUIP_EQUIPPED_TOP := "#171d23"
const EQUIP_EQUIPPED_BOTTOM := "#0d1116"
const EQUIP_EQUIPPED_BORDER := "#53636e"
const EQUIP_LOCKED_TOP := "#0d1013"
const EQUIP_LOCKED_BOTTOM := "#090c0f"
const EQUIP_LOCKED_BORDER := "#22282d"
const EQUIP_TEXT := Color("#dce2e6")
const EQUIP_TEXT_MUTED := Color("#9aa4ad")
const EQUIP_RAIL := Color("#080b0f")
const EQUIP_RIM_LIGHT := Color("#65737e")
const EQUIP_RIM_DARK := Color("#040608")

# Thin machined rim, recessed interior; no change to Control minimum sizes.
static func equipment_tray(top: String, bottom: String, edge: String, occupied := false) -> StyleBoxTexture:
	var key := str(["equipment_tray", top, bottom, edge, occupied])
	if not _cache.has(key):
		var img := Image.create(128, 128, false, Image.FORMAT_RGBA8)
		for y in 128:
			for x in 128:
				var color := Color(top).lerp(Color(bottom), float(y) / 127.0)
				if x == 0 or y == 0 or x == 127 or y == 127:
					color = Color(edge)
				elif y == 1 or x == 1:
					color = Color(edge).lerp(EQUIP_RIM_LIGHT, 0.65 if occupied else 0.2)
				elif y >= 125 or x >= 125:
					color = EQUIP_RIM_DARK
				elif y <= 3 or x <= 3:
					color = EQUIP_RIM_DARK.lerp(Color(top), 0.35)
				img.set_pixel(x, y, color)
		_cache[key] = ImageTexture.create_from_image(img)
	var box := StyleBoxTexture.new()
	box.texture = _cache[key]
	for side in [SIDE_LEFT, SIDE_TOP, SIDE_RIGHT, SIDE_BOTTOM]:
		box.set_texture_margin(side, 4)
		box.set_content_margin(side, 0)
	return box

const BACKPACK_EMPTY_TOP := Color("#0b0e12")
const BACKPACK_EMPTY_BOTTOM := Color("#0b0e12")
const BACKPACK_EMPTY_LIGHT_EDGE := Color("#1d2329")
const BACKPACK_EMPTY_DARK_EDGE := Color("#1d2329")
const BACKPACK_EMPTY_HOVER_TOP := Color("#171d23")
const BACKPACK_EMPTY_HOVER_BOTTOM := Color("#171d23")
const BACKPACK_ITEM_TILE_TOP := Color("#0b0e12")
const BACKPACK_ITEM_TILE_BOTTOM := Color("#0b0e12")
const BACKPACK_ITEM_TOP := Color("#10151a")
const BACKPACK_ITEM_BOTTOM := Color("#10151a")
const BACKPACK_ITEM_DARK_EDGE := Color("#252d34")
const BACKPACK_ITEM_LIGHT_EDGE := Color("#252d34")
const BACKPACK_ITEM_HOVER_BOTTOM := Color("#1c252d")
const BACKPACK_DRAG_BOTTOM := Color("#35434fc0")
const BACKPACK_DROP_EDGE := Color("#94abb6")
const BACKPACK_DROP_FILL := Color("#94abb629")
const BACKPACK_INVALID_FILL := Color("#6a454c29")
const BACKPACK_DROP_DURATION := 0.22
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
		if chars.begins_with("已") and size.y < chars.length() * font_size + 4:
			chars = chars.substr(1)
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
		return 42 if equipment else 32
	if crafted != null and crafted.visible:
		return 24 if equipment else 18
	return 8 if equipment else 4

static func item_shadow(label: Label, light := false) -> void:
	label.add_theme_color_override("font_shadow_color", Color(1, 1, 1, 0.7) if light else Color(0, 0, 0, 0.7))
	label.add_theme_constant_override("shadow_offset_x", 0)
	label.add_theme_constant_override("shadow_offset_y", 1)
	label.add_theme_constant_override("shadow_outline_size", 1)

static func update_item_badges(content: Control, item: Dictionary, equipment := false) -> void:
	var crafted: bool = bool(item.get("_isCrafted", false)) or not item.get("_craftData", {}).is_empty()
	for value in item.get("gunsmith_parts", {}).values():
		crafted = crafted or _enabled_part(value)
	var flags := [int(item.get("enhanceLevel", 0)) > 0, crafted, has_enchantment(item)]
	var texts := ["已强化", "已改造", "已附魔"]
	for i in 3:
		var badge := content.get_node_or_null("SourceBadge%d" % i) as VerticalBadge
		if badge == null:
			badge = VerticalBadge.new()
			badge.name = "SourceBadge%d" % i
			content.add_child(badge)
		badge.text = "\n".join(texts[i].split(""))
		badge.add_theme_font_size_override("font_size", 10 if equipment else 8)
		badge.add_theme_font_override("font", preload("res://ui/style.gd").make_font(700))
		badge.add_theme_constant_override("line_spacing", 0)
		badge.set_anchors_and_offsets_preset(Control.PRESET_LEFT_WIDE if i == 0 else Control.PRESET_RIGHT_WIDE)
		badge.offset_top = 4
		badge.offset_bottom = -4
		var width := 14 if equipment else 10
		if i == 0:
			badge.offset_left = 24 if equipment else 20
			badge.offset_right = badge.offset_left + width
		else:
			badge.offset_right = (-6 if equipment else -4) - (i - 1) * (18 if equipment else 14)
			badge.offset_left = badge.offset_right - width
		var palette: Dictionary = preload("res://ui/style.gd").GLASS_TOKENS.processing
		badge.add_theme_stylebox_override("normal", badge_surface(Color(palette[["enhanced", "crafted", "enchanted"][i]])))
		badge.add_theme_color_override("font_color", Color.BLACK if i == 0 else Color.WHITE)
		badge.visible = flags[i]

# A small rounded inset strip stays inside the rounded equipment shell.
static func badge_surface(color: Color) -> StyleBoxFlat:
	return preload("res://ui/style.gd").make_style(color, Color.TRANSPARENT, 4, 0)

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
				elif (x >= 127 or y >= 127) and top_left_edge != bottom_right_edge:
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

static func _enabled_part(value: Variant) -> bool:
	return not value.is_empty() if value is String else value == true
