extends RefCounted
const Sound := preload("res://ui/sound.gd")
## UI 风格集中定义。色值真源 = ui/palette.json（改 JSON 即可换肤，无需改代码；
## 缺失字段用下方内置默认值兜底）。生成/更新 palette.json：tools/gen-palette.ps1
## 定稿方向（DESIGN.md）：金主色 + 白信息 + 深灰底（下方 THEME_* 块）。
## 切换时用 THEME_* 色板整体替换上方旧 2D 暗金 COLOR_*，HUD/背包代码零改动。

const PALETTE_PATH := "res://ui/palette.json"
const CONFIG_PATH := "res://ui/style-config.json"

# ---------- 风格配置（style-config.json，改配置不改代码） ----------
static var ACTIVE_THEME := "dark_gold"            # dark_gold | gold_white_gray
static var RADIUS := 8
static var RADIUS_XS := 4
static var RADIUS_SM := 6
static var RADIUS_MD := 8
static var RADIUS_LG := 12
static var SPACING: Dictionary = {"grid": 4, "hud_margin": 20, "panel_padding": 10, "element_gap": 8}
static var FONT_SIZES: Dictionary = {"h1": 48, "h2": 32, "big": 22, "label": 16, "body": 14, "caption": 12}
static var FONT_WEIGHTS: Dictionary = {"heavy": 700, "bold": 600, "regular": 400}
static var MOTION_DURATION := 0.2
static var MOTION_EASING := "ease_out"

## 脚本类加载时自动执行：读取 ui/palette.json 并覆盖色板默认值
static func _static_init() -> void:
	_load_config()
	var pal := _load_palette()
	if not pal.is_empty():
		_apply_colors(pal)
	if ACTIVE_THEME == "gold_white_gray":
		_apply_theme_preset()

static func _load_config() -> void:
	if not FileAccess.file_exists(CONFIG_PATH):
		return
	var f := FileAccess.open(CONFIG_PATH, FileAccess.READ)
	if f == null:
		push_warning("ui/style.gd: cannot open style-config.json")
		return
	var parsed = JSON.parse_string(f.get_as_text())
	if typeof(parsed) != TYPE_DICTIONARY:
		push_warning("ui/style.gd: style-config.json parse failed, using defaults")
		return
	var cfg: Dictionary = parsed
	if cfg.has("active_theme"):
		var t := str(cfg.active_theme)
		if t in ["dark_gold", "gold_white_gray"]:
			ACTIVE_THEME = t
	if cfg.has("radius"):
		RADIUS = int(cfg.radius)
	if cfg.has("radius_xs"):
		RADIUS_XS = int(cfg.radius_xs)
	if cfg.has("radius_sm"):
		RADIUS_SM = int(cfg.radius_sm)
	if cfg.has("radius_md"):
		RADIUS_MD = int(cfg.radius_md)
	if cfg.has("radius_lg"):
		RADIUS_LG = int(cfg.radius_lg)
	if typeof(cfg.get("spacing", {})) == TYPE_DICTIONARY:
		for key in cfg.spacing:
			SPACING[key] = int(cfg.spacing[key])
	if typeof(cfg.get("font", {})) == TYPE_DICTIONARY:
		for key in cfg.font:
			FONT_SIZES[key] = int(cfg.font[key])
	if typeof(cfg.get("font_weight", {})) == TYPE_DICTIONARY:
		for key in cfg.font_weight:
			FONT_WEIGHTS[key] = int(cfg.font_weight[key])
	if typeof(cfg.get("motion", {})) == TYPE_DICTIONARY:
		var motion: Dictionary = cfg.motion
		if motion.has("duration_ms"):
			MOTION_DURATION = float(motion.duration_ms) / 1000.0
		if motion.has("easing"):
			MOTION_EASING = str(motion.easing)

## 风格查询（供组件统一消费，禁止散落数值）
static func spacing(key: String) -> int:
	return int(SPACING.get(key, 4))

static func font_size(key: String) -> int:
	return int(FONT_SIZES.get(key, 14))

static func font_weight(key: String) -> int:
	return int(FONT_WEIGHTS.get(key, 400))

static func theme_active() -> String:
	return ACTIVE_THEME

static func _load_palette() -> Dictionary:
	if not FileAccess.file_exists(PALETTE_PATH):
		return {}
	var f := FileAccess.open(PALETTE_PATH, FileAccess.READ)
	if f == null:
		push_warning("ui/style.gd: cannot open palette.json")
		return {}
	var parsed = JSON.parse_string(f.get_as_text())
	if typeof(parsed) != TYPE_DICTIONARY:
		push_warning("ui/style.gd: palette.json parse failed, using built-in defaults")
		return {}
	var pal: Dictionary = parsed
	var colors = pal.get("colors", {})
	if typeof(colors) != TYPE_DICTIONARY:
		colors = {}
	for key in colors:
		pal[key] = colors[key]
	return pal

## #RGB / #RRGGBB / #RRGGBBAA -> Color
static func _hex_to_color(hex: String) -> Color:
	var s := hex.strip_edges().trim_prefix("#")
	if s.length() == 3:
		return Color("#" + s[0] + s[0] + s[1] + s[1] + s[2] + s[2])
	if s.length() == 6 or s.length() == 8:
		return Color("#" + s)
	push_warning("ui/style.gd: invalid color %s" % hex)
	return Color.WHITE

# ---------- 基础色板（旧版 2D 暗金棕，精确对齐 style.css / game-style.css） ----------
static var COLOR_BAR_BG: Color = Color(0.1647, 0.1451, 0.1255, 0.9) # rgba(42,37,32,0.9)
static var COLOR_BAR_BORDER: Color = Color(0.3529, 0.3020, 0.2471) # #5a4d3f
static var COLOR_SLOT_BG: Color = Color(0.2392, 0.2039, 0.1686) # #3d342b
static var COLOR_SLOT_TINT_EMPTY: Color = Color(1.0, 1.0, 1.0)
static var COLOR_SLOT_TINT_ITEM: Color = Color(1.06, 1.04, 0.98)
static var COLOR_SLOT_TINT_HOVER: Color = Color(1.0, 0.90, 0.70)
static var COLOR_SLOT_TINT_DRAG: Color = Color(1.0, 0.84, 0.55)
static var COLOR_EQUIP_TINT_EQUIPPED: Color = Color(1.08, 1.06, 0.97)
static var COLOR_EQUIP_TINT_LOCKED: Color = Color(0.56, 0.56, 0.60)
static var COLOR_SLOT_BORDER: Color = Color(0.3529, 0.3020, 0.2471) # #5a4d3f
static var COLOR_SLOT_HOVER_BG: Color = Color(0.2902, 0.2471, 0.2078) # #4a3f35
static var COLOR_SLOT_HOVER_BORDER: Color = Color(0.5412, 0.4902, 0.4196) # #8a7d6b
static var COLOR_ITEM_BG: Color = Color(0.2392, 0.2902, 0.2078) # #3d4a35（占用）
static var COLOR_ITEM_BORDER: Color = Color(0.4784, 0.6039, 0.4157) # #7a9a6a（占用）
static var COLOR_DRAG_OVER_BG: Color = Color(0.2902, 0.2471, 0.2078) # #4a3f35
static var COLOR_DRAG_OVER_BORDER: Color = Color(0.8314, 0.7725, 0.6627) # #d4c5a9
static var COLOR_EQUIP_SLOT_BG: Color = Color(0.2392, 0.2039, 0.1686) # #3d342b
static var COLOR_EQUIP_SLOT_BORDER: Color = Color(0.3529, 0.3020, 0.2471) # #5a4d3f
static var COLOR_EQUIP_EQUIPPED_BG: Color = Color(0.3137, 0.3137, 0.3137, 0.95) # rgba(80,80,80,0.95)
static var COLOR_EQUIP_EQUIPPED_BORDER: Color = Color(0.4706, 0.4706, 0.4706, 0.7) # rgba(120,120,120,0.7)
static var COLOR_EQUIP_LOCKED_BG: Color = Color(0.4706, 0.4706, 0.4706, 0.6) # rgba(120,120,120,0.6)
static var COLOR_EQUIP_LOCKED_BORDER: Color = Color(0.2667, 0.2667, 0.2667) # #444
static var COLOR_PANEL_BG: Color = Color(0.0784, 0.0784, 0.0980, 0.8) # rgba(20,20,25,0.8)
static var COLOR_PANEL_BORDER: Color = Color(0.2353, 0.2353, 0.2745, 0.5) # rgba(60,60,70,0.5)
static var COLOR_OVERLAY: Color = Color(0, 0, 0, 0.3) # rgba(0,0,0,0.3)
static var COLOR_TEXT: Color = Color(0.8314, 0.7725, 0.6627) # #d4c5a9
static var COLOR_DIM_TEXT: Color = Color(0.5412, 0.4902, 0.4196) # #8a7d6b
static var COLOR_MUTED: Color = Color(0.4196, 0.3647, 0.3098) # #6b5d4f
static var COLOR_NOTICE: Color = Color(0.8314, 0.7725, 0.6627) # #d4c5a9
static var COLOR_STATUS: Color = Color(0.8314, 0.7725, 0.6627) # #d4c5a9
static var COLOR_AMMO: Color = Color(0.8314, 0.7725, 0.6627) # #d4c5a9
static var COLOR_KILL: Color = Color(0.8314, 0.7725, 0.6627) # #d4c5a9
static var COLOR_HP_BG: Color = Color(0.1647, 0.1451, 0.1255, 0.85) # rgba(42,37,32,0.85) 顶栏底
static var COLOR_HP_HIGH: Color = Color(0.6275, 0.3765, 0.3765) # #a06060（旧版红棕血条）
static var COLOR_HP_MID: Color = Color(0.5412, 0.2902, 0.2902) # #8a4a4a
static var COLOR_HP_LOW: Color = Color(0.4784, 0.2275, 0.2275) # #7a3a3a
static var COLOR_MP_FILL: Color = Color(0.2902, 0.4157, 0.5412) # #4a6a8a
static var COLOR_STAMINA_FILL: Color = Color(0.4784, 0.5412, 0.2902) # #7a8a4a
static var COLOR_EXP_FILL: Color = Color(0.5412, 0.4784, 0.2902) # #8a7a4a
static var COLOR_BAR_TRACK: Color = Color(0.15, 0.13, 0.11, 0.9)
static var COLOR_DEATH_TITLE: Color = Color(0.95, 0.4, 0.35)
static var COLOR_DEATH_HINT: Color = Color(0.8314, 0.7725, 0.6627) # #d4c5a9
static var COLOR_CROSSHAIR: Color = Color(0.95, 0.95, 0.9)
static var COLOR_HITMARKER: Color = Color(0.98, 0.98, 0.95)
static var COLOR_DMG_FLASH: Color = Color(0.8, 0, 0, 0)
static var COLOR_TRANSPARENT: Color = Color(0, 0, 0, 0)
static var COLOR_WHITE: Color = Color(1, 1, 1)
static var COLOR_BLACK: Color = Color(0, 0, 0)
static var COLOR_TITLE_TEXT: Color = Color(0.8314, 0.7725, 0.6627) # #d4c5a9
static var COLOR_STACK_TEXT: Color = Color(0.8314, 0.7725, 0.6627) # #d4c5a9
static var COLOR_KEY_HINT: Color = Color(1, 1, 1) # #ffffff（旧版快捷栏键位）
static var COLOR_ZERO_TEXT: Color = Color(0.95, 0.35, 0.32)
static var COLOR_RARITY_TEXT: Color = Color(0.1, 0.1, 0.1)
static var COLOR_EQUIP_LOCK_OVERLAY: Color = Color(0.12, 0.12, 0.12, 0.62)
static var COLOR_DRAG_PREVIEW_BG: Color = Color(0.2, 0.18, 0.15, 0.92)
static var COLOR_SKILL_SLOT_BG: Color = Color(0.2392, 0.2039, 0.1686) # #3d342b 技能槽（旧版 quick-slot.skill）
static var COLOR_SKILL_SLOT_BORDER: Color = Color(0.4196, 0.3647, 0.3098) # #6b5d4f

# ---------- 浮窗（白底，复刻旧版 tt-main） ----------
static var COLOR_TT_BG: Color = Color(0.96, 0.96, 0.96) # 旧版白底浮窗渐变近似
static var COLOR_TT_BORDER: Color = Color(0, 0, 0, 0.2) # rgba(0,0,0,0.2)
static var COLOR_TT_NAME: Color = Color(0.16, 0.145, 0.125)
static var COLOR_TT_TYPE: Color = Color(0.29, 0.247, 0.208)
static var COLOR_TT_VAL: Color = Color(0.16, 0.145, 0.125)
static var COLOR_TT_POS: Color = Color(0.165, 0.478, 0.165)
static var COLOR_TT_DESC: Color = Color(0.42, 0.365, 0.31)
static var COLOR_TT_CLOSE_BG: Color = Color(0.78, 0.2, 0.2, 0.8)
static var COLOR_TT_CLOSE_HOVER: Color = Color(0.86, 0.27, 0.27)
static var COLOR_TT_SECTION_BORDER: Color = Color(0, 0, 0, 0.12)
static var COLOR_TT_CRAFT_POS: Color = Color(0, 0.6, 0)
static var COLOR_TT_CRAFT_NEG: Color = Color(0.85, 0, 0)
static var COLOR_TT_ENCHANT_NAME: Color = Color(0.75, 0.63, 0.38)
static var COLOR_TT_SHADOW: Color = Color(0, 0, 0, 0.4) # 浮窗阴影（旧版 box-shadow 等效）
static var COLOR_BADGE_GOLD_BG: Color = Color(1.0, 0.84, 0.0, 0.92)
static var COLOR_BADGE_GOLD_TEXT: Color = Color(0.1, 0.1, 0.18)
static var COLOR_BADGE_CRAFT_BG: Color = Color(0.42, 0.62, 0.9, 0.92)
static var COLOR_BADGE_CRAFT_TEXT: Color = Color(0.95, 0.97, 1.0)
static var COLOR_BADGE_ENCHANT_BG: Color = Color(0.66, 0.42, 0.85, 0.92)
static var COLOR_BADGE_ENCHANT_TEXT: Color = Color(0.98, 0.95, 1.0) # ---------- 稀有度（对齐旧版 src/config/rarity.js） ----------
const RARITY_LABELS := {
	"common": "普通",
	"uncommon": "优质",
	"rare": "稀有",
	"epic": "史诗",
	"mythic": "神话",
	"legendary": "传说",
}
static var RARITY_COLORS: Dictionary = {
	"common": Color(0.7529, 0.7529, 0.7529),
	"uncommon": Color(0.4784, 1.0, 0.4784),
	"rare": Color(0.4784, 0.6039, 1.0),
	"epic": Color(0.7765, 0.4784, 1.0),
	"mythic": Color(0.9020, 0.6039, 0.2353),
	"legendary": Color(0.8784, 0.2902, 0.2275),
}
## 装备槽稀有度竖排徽章底色（半透明，对齐旧版 .slot-rarity.rarity-*）
static var RARITY_BADGE_COLORS: Dictionary = {
	"common": Color(0.71, 0.71, 0.71, 0.85),
	"uncommon": Color(0.48, 0.78, 0.48, 0.7),
	"rare": Color(0.48, 0.62, 0.78, 0.7),
	"epic": Color(0.71, 0.48, 0.78, 0.7),
	"mythic": Color(0.9, 0.59, 0.24, 0.78),
	"legendary": Color(0.84, 0.24, 0.22, 0.8),
}

# ---------- 定稿金色板（DESIGN.md Token，未启用） ----------
# 全境封锁 UI 改进情绪板定稿：金主色 + 白信息 + 深灰底。
# 切换时用下方色板整体替换上方旧 2D 暗金 COLOR_*，HUD/背包代码零改动。
static var THEME_BG: Color = Color(0.0588, 0.0588, 0.0627) # #0F0F10 深灰黑底
static var THEME_GOLD: Color = Color(0.8314, 0.6863, 0.2157) # #D4AF37 核心强调
static var THEME_WHITE: Color = Color(1, 1, 1) # #FFFFFF 主信息文本
static var THEME_GRAY_LIGHT: Color = Color(0.7098, 0.7098, 0.7098) # #B5B5B5 次级文本/禁用字
static var THEME_GRAY_MID: Color = Color(0.2275, 0.2275, 0.2353) # #3A3A3C 边框/分隔线/按钮底
static var THEME_HP_GREEN: Color = Color(0.498, 0.824, 0.416) # #7FD26A 生命（状态）
static var THEME_WARN_ORANGE: Color = Color(0.878, 0.663, 0.310) # #E0A94F 警告（状态）
static var THEME_DANGER_RED: Color = Color(0.851, 0.357, 0.290) # #D95B4A 危险（状态）
static var THEME_MP_BLUE: Color = Color(0.353, 0.561, 0.878) # #5A8FE0 魔力（状态）
# 按钮三态 / 进度条 / 分隔线（DESIGN.md 第 5 节）
static var THEME_BTN_BG: Color = Color(0.2275, 0.2275, 0.2353) # 默认底（同 GRAY_MID）
static var THEME_BTN_HOVER_BG: Color = Color(0.8314, 0.6863, 0.2157) # 悬停金底
static var THEME_BTN_DISABLED_BG: Color = Color(0.2275, 0.2275, 0.2353) # 禁用底
static var THEME_BTN_DISABLED_TEXT: Color = Color(0.7098, 0.7098, 0.7098) # 禁用字
static var THEME_PROGRESS_FILL: Color = Color(0.8314, 0.6863, 0.2157) # 进度条金填充
static var THEME_DIVIDER: Color = Color(0.2275, 0.2275, 0.2353) # 细分隔线
static var THEME_DIVIDER_ACCENT: Color = Color(0.8314, 0.6863, 0.2157, 0.6) # 金色强调分隔线

# ---------- 字体 ----------

## 黑体字重阶梯（DESIGN.md：标题 Heavy / 副标题 Bold / 正文 Regular）
## 字体文件直载（绕开系统字体名解析，确保 100% 生效）：
## - 正文/常规：微软雅黑 MicrosoftYaHei.ttc
## - 加粗/标题：微软雅黑 Bold MicrosoftYaHeiBold.ttc
## - 等宽数字：Consolas.ttf（VS Code 同款）
static var _font_regular: Font
static var _font_bold: Font
static var _font_mono: Font

static func make_font(weight := 400) -> Font:
	if weight >= 600:
		if _font_bold == null:
			_font_bold = load("res://assets/ui/fonts/MicrosoftYaHeiBold.ttc")
		return _font_bold
	if _font_regular == null:
		_font_regular = load("res://assets/ui/fonts/MicrosoftYaHei.ttc")
	return _font_regular

## 等宽字体（VS Code Consolas 同款）：HUD 数字/弹药/数值用，清晰对齐
static func make_mono_font(_weight := 400) -> Font:
	if _font_mono == null:
		_font_mono = load("res://assets/ui/fonts/Consolas.ttf")
	return _font_mono

## emoji 回退字体（旧版图标加载失败时显示 item.icon 字符）
static func make_emoji_font() -> SystemFont:
	var f := SystemFont.new()
	f.font_names = PackedStringArray(["Segoe UI Emoji", "Noto Color Emoji", "Apple Color Emoji"])
	return f

static func make_theme() -> Theme:
	var t := Theme.new()
	t.default_font = make_font()
	t.default_font_size = 14
	return t

static func make_style(bg: Color, border: Color, radius := -1, border_w := 2) -> StyleBoxFlat:
	var sb := StyleBoxFlat.new()
	sb.bg_color = bg
	sb.border_color = border
	sb.set_border_width_all(border_w)
	sb.set_corner_radius_all(RADIUS if radius < 0 else radius)
	return sb

## 格子样式统一入口：size_class = xs(快捷栏 4px) / sm(背包格 6px) / md(装备槽 8px)
static func make_slot_style(bg: Color, border: Color, size_class := "sm", border_w := 1) -> StyleBoxFlat:
	var r := RADIUS_XS if size_class == "xs" else (RADIUS_MD if size_class == "md" else RADIUS_SM)
	return make_style(bg, border, r, border_w)

## 按钮三态样式（DESIGN.md 第 5 节）：{normal, hover, pressed, disabled}
static func make_button_style() -> Dictionary:
	# Vega：rounded-md(6px)、px-2.5(10px) / py-1.5(6px)、1px 边框、禁用 50% 透明
	var base_margin := {"content_margin_left": 10, "content_margin_right": 10,
		"content_margin_top": 6, "content_margin_bottom": 6}
	var normal := make_style(THEME_BTN_BG, THEME_GRAY_MID, RADIUS_SM, 1)
	var hover := make_style(THEME_BTN_HOVER_BG, THEME_GOLD, RADIUS_SM, 1)
	var pressed := make_style(Color(THEME_GOLD, 0.85), THEME_GOLD, RADIUS_SM, 1)
	var disabled := make_style(Color(THEME_BTN_DISABLED_BG, 0.5), THEME_GRAY_MID, RADIUS_SM, 1)
	for sb in [normal, hover, pressed, disabled]:
		for k in base_margin:
			sb.set(k, base_margin[k])
	pressed.content_margin_top = int(base_margin["content_margin_top"]) + 1  # 按下内容下沉 1px
	return {"normal": normal, "hover": hover, "pressed": pressed, "disabled": disabled}

## 面板样式（玻璃感：半透明深灰底 + 细边框）
static func make_panel_style() -> StyleBoxFlat:
	# Vega：rounded-lg(8px)、1px 边框
	var sb := make_style(Color(THEME_BG, 0.8), THEME_GRAY_MID, RADIUS_MD, 1)
	sb.content_margin_left = SPACING.get("panel_padding", 10)
	sb.content_margin_right = SPACING.get("panel_padding", 10)
	sb.content_margin_top = SPACING.get("panel_padding", 10)
	sb.content_margin_bottom = SPACING.get("panel_padding", 10)
	return sb

## 纹理面板（程序化生成深灰磨砂金属底纹，九宫格平铺；纹理：assets/ui/textures/panel_brushed.png）
## 内嵌卡面板（属性页分区卡片）：略亮底 + 顶部高光 + 1px 细框（textures/panel_inner.png）
static func make_inner_panel_style() -> StyleBoxTexture:
	var sb := StyleBoxTexture.new()
	sb.texture = load("res://assets/ui/textures/panel_inner.png")
	sb.modulate_color = Color(1, 1, 1, 0.72)
	var m := 12
	sb.texture_margin_left = m
	sb.texture_margin_right = m
	sb.texture_margin_top = m
	sb.texture_margin_bottom = m
	sb.axis_stretch_horizontal = StyleBoxTexture.AXIS_STRETCH_MODE_TILE
	sb.axis_stretch_vertical = StyleBoxTexture.AXIS_STRETCH_MODE_TILE
	sb.content_margin_left = 10
	sb.content_margin_right = 10
	sb.content_margin_top = 8
	sb.content_margin_bottom = 8
	return sb

## 半透明毛玻璃主面板：深灰半透明底 + 1px 细框 + 投影；毛玻璃质感由面板背后 blur 层提供
static func make_glass_panel_style(radius := -1, bg_alpha := 0.30) -> StyleBox:
	var sb := StyleBoxFlat.new()
	sb.bg_color = Color(THEME_BG, bg_alpha)
	sb.border_color = Color(THEME_GRAY_MID, 0.65)
	sb.set_border_width_all(1)
	sb.set_corner_radius_all(RADIUS_MD if radius < 0 else radius)
	sb.shadow_color = Color(0, 0, 0, 0.45)
	sb.shadow_size = 16
	sb.shadow_offset = Vector2(0, 4)
	sb.content_margin_left = SPACING.get("panel_padding", 10)
	sb.content_margin_right = SPACING.get("panel_padding", 10)
	sb.content_margin_top = SPACING.get("panel_padding", 10)
	sb.content_margin_bottom = SPACING.get("panel_padding", 10)
	return sb

## 格子底纹理（背包/快捷栏/装备槽共用）：textures/panel_slot.png，modulate 控制状态色
static func make_slot_texture_style(modulate := Color(1, 1, 1, 1)) -> StyleBoxTexture:
	var sb := StyleBoxTexture.new()
	sb.texture = load("res://assets/ui/textures/panel_slot.png")
	sb.modulate_color = modulate
	var m := 6
	sb.texture_margin_left = m
	sb.texture_margin_right = m
	sb.texture_margin_top = m
	sb.texture_margin_bottom = m
	sb.axis_stretch_horizontal = StyleBoxTexture.AXIS_STRETCH_MODE_TILE
	sb.axis_stretch_vertical = StyleBoxTexture.AXIS_STRETCH_MODE_TILE
	sb.content_margin_left = 4
	sb.content_margin_right = 4
	sb.content_margin_top = 4
	sb.content_margin_bottom = 4
	return sb

## 页签激活态：金上暗下 + 顶底金线（textures/panel_tab.png）
static func make_tab_active_style() -> StyleBoxTexture:
	var sb := StyleBoxTexture.new()
	sb.texture = load("res://assets/ui/textures/panel_tab.png")
	var m := 12
	sb.texture_margin_left = m
	sb.texture_margin_right = m
	sb.texture_margin_top = m
	sb.texture_margin_bottom = m
	sb.axis_stretch_horizontal = StyleBoxTexture.AXIS_STRETCH_MODE_TILE
	sb.axis_stretch_vertical = StyleBoxTexture.AXIS_STRETCH_MODE_TILE
	sb.content_margin_left = 10
	sb.content_margin_right = 10
	sb.content_margin_top = 6
	sb.content_margin_bottom = 6
	return sb

static func make_texture_panel_style(radius := -1) -> StyleBoxTexture:
	var sb := StyleBoxTexture.new()
	sb.texture = load("res://assets/ui/textures/panel_main.png")
	sb.modulate_color = Color(1, 1, 1, 1)
	var m := 28
	sb.texture_margin_left = m
	sb.texture_margin_right = m
	sb.texture_margin_top = m
	sb.texture_margin_bottom = m
	sb.axis_stretch_horizontal = StyleBoxTexture.AXIS_STRETCH_MODE_TILE
	sb.axis_stretch_vertical = StyleBoxTexture.AXIS_STRETCH_MODE_TILE
	sb.content_margin_left = SPACING.get("panel_padding", 10)
	sb.content_margin_right = SPACING.get("panel_padding", 10)
	sb.content_margin_top = SPACING.get("panel_padding", 10)
	sb.content_margin_bottom = SPACING.get("panel_padding", 10)
	return sb

## 给 Button 应用三态样式 + 字号
static func style_button(btn: Button, font_size_key := "body") -> void:
	var s := make_button_style()
	btn.add_theme_stylebox_override("normal", s.normal)
	btn.add_theme_stylebox_override("hover", s.hover)
	btn.add_theme_stylebox_override("pressed", s.pressed)
	btn.add_theme_stylebox_override("disabled", s.disabled)
	btn.add_theme_font_size_override("font_size", font_size(font_size_key))
	btn.add_theme_color_override("font_color", THEME_WHITE)
	btn.add_theme_color_override("font_hover_color", Color(THEME_BG, 1.0))
	btn.add_theme_color_override("font_pressed_color", Color(THEME_BG, 1.0))
	btn.add_theme_color_override("font_disabled_color", Color(THEME_BTN_DISABLED_TEXT, 0.5))
	_attach_button_anim(btn)

## 统一按钮动画（Vega 规范）：hover 微放大 1.03，按下微缩 0.97（+ pressed 样式下沉 1px）
static func _attach_button_anim(btn: Button) -> void:
	btn.pivot_offset = btn.size * 0.5
	btn.mouse_entered.connect(func() -> void:
		Sound.hover()
		_button_scale(btn, 1.03))
	btn.mouse_exited.connect(func() -> void: _button_scale(btn, 1.0))
	btn.button_down.connect(func() -> void:
		Sound.click()
		_button_scale(btn, 0.97))
	btn.button_up.connect(func() -> void: _button_scale(btn, 1.03))

static func _button_scale(btn: Button, target: float) -> void:
	if not btn.is_inside_tree():
		return
	btn.pivot_offset = btn.size * 0.5
	var tw := btn.create_tween()
	tw.tween_property(btn, "scale", Vector2(target, target), 0.08) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)

static func rarity_label(key: String) -> String:
	return String(RARITY_LABELS.get(key, key))

static func rarity_color(key: String) -> Color:
	return RARITY_COLORS.get(key, Color.WHITE)

## 用 palette.json 的值覆盖色板（只有 json 里出现的键会被覆盖）
static func _apply_colors(p: Dictionary) -> void:
	if p.has("COLOR_AMMO"): COLOR_AMMO = _hex_to_color(p.COLOR_AMMO)
	if p.has("COLOR_BADGE_CRAFT_BG"): COLOR_BADGE_CRAFT_BG = _hex_to_color(p.COLOR_BADGE_CRAFT_BG)
	if p.has("COLOR_BADGE_CRAFT_TEXT"): COLOR_BADGE_CRAFT_TEXT = _hex_to_color(p.COLOR_BADGE_CRAFT_TEXT)
	if p.has("COLOR_BADGE_ENCHANT_BG"): COLOR_BADGE_ENCHANT_BG = _hex_to_color(p.COLOR_BADGE_ENCHANT_BG)
	if p.has("COLOR_BADGE_ENCHANT_TEXT"): COLOR_BADGE_ENCHANT_TEXT = _hex_to_color(p.COLOR_BADGE_ENCHANT_TEXT)
	if p.has("COLOR_BADGE_GOLD_BG"): COLOR_BADGE_GOLD_BG = _hex_to_color(p.COLOR_BADGE_GOLD_BG)
	if p.has("COLOR_BADGE_GOLD_TEXT"): COLOR_BADGE_GOLD_TEXT = _hex_to_color(p.COLOR_BADGE_GOLD_TEXT)
	if p.has("COLOR_BAR_BG"): COLOR_BAR_BG = _hex_to_color(p.COLOR_BAR_BG)
	if p.has("COLOR_BAR_BORDER"): COLOR_BAR_BORDER = _hex_to_color(p.COLOR_BAR_BORDER)
	if p.has("COLOR_BAR_TRACK"): COLOR_BAR_TRACK = _hex_to_color(p.COLOR_BAR_TRACK)
	if p.has("COLOR_BLACK"): COLOR_BLACK = _hex_to_color(p.COLOR_BLACK)
	if p.has("COLOR_CROSSHAIR"): COLOR_CROSSHAIR = _hex_to_color(p.COLOR_CROSSHAIR)
	if p.has("COLOR_DEATH_HINT"): COLOR_DEATH_HINT = _hex_to_color(p.COLOR_DEATH_HINT)
	if p.has("COLOR_DEATH_TITLE"): COLOR_DEATH_TITLE = _hex_to_color(p.COLOR_DEATH_TITLE)
	if p.has("COLOR_DIM_TEXT"): COLOR_DIM_TEXT = _hex_to_color(p.COLOR_DIM_TEXT)
	if p.has("COLOR_DMG_FLASH"): COLOR_DMG_FLASH = _hex_to_color(p.COLOR_DMG_FLASH)
	if p.has("COLOR_DRAG_OVER_BG"): COLOR_DRAG_OVER_BG = _hex_to_color(p.COLOR_DRAG_OVER_BG)
	if p.has("COLOR_DRAG_OVER_BORDER"): COLOR_DRAG_OVER_BORDER = _hex_to_color(p.COLOR_DRAG_OVER_BORDER)
	if p.has("COLOR_DRAG_PREVIEW_BG"): COLOR_DRAG_PREVIEW_BG = _hex_to_color(p.COLOR_DRAG_PREVIEW_BG)
	if p.has("COLOR_SKILL_SLOT_BG"): COLOR_SKILL_SLOT_BG = _hex_to_color(p.COLOR_SKILL_SLOT_BG)
	if p.has("COLOR_SKILL_SLOT_BORDER"): COLOR_SKILL_SLOT_BORDER = _hex_to_color(p.COLOR_SKILL_SLOT_BORDER)
	if p.has("COLOR_EQUIP_EQUIPPED_BG"): COLOR_EQUIP_EQUIPPED_BG = _hex_to_color(p.COLOR_EQUIP_EQUIPPED_BG)
	if p.has("COLOR_EQUIP_EQUIPPED_BORDER"): COLOR_EQUIP_EQUIPPED_BORDER = _hex_to_color(p.COLOR_EQUIP_EQUIPPED_BORDER)
	if p.has("COLOR_EQUIP_LOCK_OVERLAY"): COLOR_EQUIP_LOCK_OVERLAY = _hex_to_color(p.COLOR_EQUIP_LOCK_OVERLAY)
	if p.has("COLOR_EQUIP_LOCKED_BG"): COLOR_EQUIP_LOCKED_BG = _hex_to_color(p.COLOR_EQUIP_LOCKED_BG)
	if p.has("COLOR_EQUIP_LOCKED_BORDER"): COLOR_EQUIP_LOCKED_BORDER = _hex_to_color(p.COLOR_EQUIP_LOCKED_BORDER)
	if p.has("COLOR_EQUIP_SLOT_BG"): COLOR_EQUIP_SLOT_BG = _hex_to_color(p.COLOR_EQUIP_SLOT_BG)
	if p.has("COLOR_EQUIP_SLOT_BORDER"): COLOR_EQUIP_SLOT_BORDER = _hex_to_color(p.COLOR_EQUIP_SLOT_BORDER)
	if p.has("COLOR_EXP_FILL"): COLOR_EXP_FILL = _hex_to_color(p.COLOR_EXP_FILL)
	if p.has("COLOR_HITMARKER"): COLOR_HITMARKER = _hex_to_color(p.COLOR_HITMARKER)
	if p.has("COLOR_HP_BG"): COLOR_HP_BG = _hex_to_color(p.COLOR_HP_BG)
	if p.has("COLOR_HP_HIGH"): COLOR_HP_HIGH = _hex_to_color(p.COLOR_HP_HIGH)
	if p.has("COLOR_HP_LOW"): COLOR_HP_LOW = _hex_to_color(p.COLOR_HP_LOW)
	if p.has("COLOR_HP_MID"): COLOR_HP_MID = _hex_to_color(p.COLOR_HP_MID)
	if p.has("COLOR_ITEM_BG"): COLOR_ITEM_BG = _hex_to_color(p.COLOR_ITEM_BG)
	if p.has("COLOR_ITEM_BORDER"): COLOR_ITEM_BORDER = _hex_to_color(p.COLOR_ITEM_BORDER)
	if p.has("COLOR_KEY_HINT"): COLOR_KEY_HINT = _hex_to_color(p.COLOR_KEY_HINT)
	if p.has("COLOR_KILL"): COLOR_KILL = _hex_to_color(p.COLOR_KILL)
	if p.has("COLOR_MP_FILL"): COLOR_MP_FILL = _hex_to_color(p.COLOR_MP_FILL)
	if p.has("COLOR_MUTED"): COLOR_MUTED = _hex_to_color(p.COLOR_MUTED)
	if p.has("COLOR_NOTICE"): COLOR_NOTICE = _hex_to_color(p.COLOR_NOTICE)
	if p.has("COLOR_OVERLAY"): COLOR_OVERLAY = _hex_to_color(p.COLOR_OVERLAY)
	if p.has("COLOR_PANEL_BG"): COLOR_PANEL_BG = _hex_to_color(p.COLOR_PANEL_BG)
	if p.has("COLOR_PANEL_BORDER"): COLOR_PANEL_BORDER = _hex_to_color(p.COLOR_PANEL_BORDER)
	if p.has("COLOR_RARITY_TEXT"): COLOR_RARITY_TEXT = _hex_to_color(p.COLOR_RARITY_TEXT)
	if p.has("COLOR_SLOT_BG"): COLOR_SLOT_BG = _hex_to_color(p.COLOR_SLOT_BG)
	if p.has("COLOR_SLOT_TINT_EMPTY"): COLOR_SLOT_TINT_EMPTY = _hex_to_color(p.COLOR_SLOT_TINT_EMPTY)
	if p.has("COLOR_SLOT_TINT_ITEM"): COLOR_SLOT_TINT_ITEM = _hex_to_color(p.COLOR_SLOT_TINT_ITEM)
	if p.has("COLOR_SLOT_TINT_HOVER"): COLOR_SLOT_TINT_HOVER = _hex_to_color(p.COLOR_SLOT_TINT_HOVER)
	if p.has("COLOR_SLOT_TINT_DRAG"): COLOR_SLOT_TINT_DRAG = _hex_to_color(p.COLOR_SLOT_TINT_DRAG)
	if p.has("COLOR_EQUIP_TINT_EQUIPPED"): COLOR_EQUIP_TINT_EQUIPPED = _hex_to_color(p.COLOR_EQUIP_TINT_EQUIPPED)
	if p.has("COLOR_EQUIP_TINT_LOCKED"): COLOR_EQUIP_TINT_LOCKED = _hex_to_color(p.COLOR_EQUIP_TINT_LOCKED)
	if p.has("COLOR_SLOT_BORDER"): COLOR_SLOT_BORDER = _hex_to_color(p.COLOR_SLOT_BORDER)
	if p.has("COLOR_SLOT_HOVER_BG"): COLOR_SLOT_HOVER_BG = _hex_to_color(p.COLOR_SLOT_HOVER_BG)
	if p.has("COLOR_SLOT_HOVER_BORDER"): COLOR_SLOT_HOVER_BORDER = _hex_to_color(p.COLOR_SLOT_HOVER_BORDER)
	if p.has("COLOR_STACK_TEXT"): COLOR_STACK_TEXT = _hex_to_color(p.COLOR_STACK_TEXT)
	if p.has("COLOR_STAMINA_FILL"): COLOR_STAMINA_FILL = _hex_to_color(p.COLOR_STAMINA_FILL)
	if p.has("COLOR_STATUS"): COLOR_STATUS = _hex_to_color(p.COLOR_STATUS)
	if p.has("COLOR_TEXT"): COLOR_TEXT = _hex_to_color(p.COLOR_TEXT)
	if p.has("COLOR_TITLE_TEXT"): COLOR_TITLE_TEXT = _hex_to_color(p.COLOR_TITLE_TEXT)
	if p.has("COLOR_TRANSPARENT"): COLOR_TRANSPARENT = _hex_to_color(p.COLOR_TRANSPARENT)
	if p.has("COLOR_TT_BG"): COLOR_TT_BG = _hex_to_color(p.COLOR_TT_BG)
	if p.has("COLOR_TT_BORDER"): COLOR_TT_BORDER = _hex_to_color(p.COLOR_TT_BORDER)
	if p.has("COLOR_TT_CLOSE_BG"): COLOR_TT_CLOSE_BG = _hex_to_color(p.COLOR_TT_CLOSE_BG)
	if p.has("COLOR_TT_CLOSE_HOVER"): COLOR_TT_CLOSE_HOVER = _hex_to_color(p.COLOR_TT_CLOSE_HOVER)
	if p.has("COLOR_TT_CRAFT_NEG"): COLOR_TT_CRAFT_NEG = _hex_to_color(p.COLOR_TT_CRAFT_NEG)
	if p.has("COLOR_TT_CRAFT_POS"): COLOR_TT_CRAFT_POS = _hex_to_color(p.COLOR_TT_CRAFT_POS)
	if p.has("COLOR_TT_DESC"): COLOR_TT_DESC = _hex_to_color(p.COLOR_TT_DESC)
	if p.has("COLOR_TT_ENCHANT_NAME"): COLOR_TT_ENCHANT_NAME = _hex_to_color(p.COLOR_TT_ENCHANT_NAME)
	if p.has("COLOR_TT_SHADOW"): COLOR_TT_SHADOW = _hex_to_color(p.COLOR_TT_SHADOW)
	if p.has("COLOR_TT_NAME"): COLOR_TT_NAME = _hex_to_color(p.COLOR_TT_NAME)
	if p.has("COLOR_TT_POS"): COLOR_TT_POS = _hex_to_color(p.COLOR_TT_POS)
	if p.has("COLOR_TT_SECTION_BORDER"): COLOR_TT_SECTION_BORDER = _hex_to_color(p.COLOR_TT_SECTION_BORDER)
	if p.has("COLOR_TT_TYPE"): COLOR_TT_TYPE = _hex_to_color(p.COLOR_TT_TYPE)
	if p.has("COLOR_TT_VAL"): COLOR_TT_VAL = _hex_to_color(p.COLOR_TT_VAL)
	if p.has("COLOR_WHITE"): COLOR_WHITE = _hex_to_color(p.COLOR_WHITE)
	if p.has("COLOR_ZERO_TEXT"): COLOR_ZERO_TEXT = _hex_to_color(p.COLOR_ZERO_TEXT)
	if p.has("THEME_BG"): THEME_BG = _hex_to_color(p.THEME_BG)
	if p.has("THEME_BTN_BG"): THEME_BTN_BG = _hex_to_color(p.THEME_BTN_BG)
	if p.has("THEME_BTN_DISABLED_BG"): THEME_BTN_DISABLED_BG = _hex_to_color(p.THEME_BTN_DISABLED_BG)
	if p.has("THEME_BTN_DISABLED_TEXT"): THEME_BTN_DISABLED_TEXT = _hex_to_color(p.THEME_BTN_DISABLED_TEXT)
	if p.has("THEME_BTN_HOVER_BG"): THEME_BTN_HOVER_BG = _hex_to_color(p.THEME_BTN_HOVER_BG)
	if p.has("THEME_DANGER_RED"): THEME_DANGER_RED = _hex_to_color(p.THEME_DANGER_RED)
	if p.has("THEME_DIVIDER"): THEME_DIVIDER = _hex_to_color(p.THEME_DIVIDER)
	if p.has("THEME_DIVIDER_ACCENT"): THEME_DIVIDER_ACCENT = _hex_to_color(p.THEME_DIVIDER_ACCENT)
	if p.has("THEME_GOLD"): THEME_GOLD = _hex_to_color(p.THEME_GOLD)
	if p.has("THEME_GRAY_LIGHT"): THEME_GRAY_LIGHT = _hex_to_color(p.THEME_GRAY_LIGHT)
	if p.has("THEME_GRAY_MID"): THEME_GRAY_MID = _hex_to_color(p.THEME_GRAY_MID)
	if p.has("THEME_HP_GREEN"): THEME_HP_GREEN = _hex_to_color(p.THEME_HP_GREEN)
	if p.has("THEME_MP_BLUE"): THEME_MP_BLUE = _hex_to_color(p.THEME_MP_BLUE)
	if p.has("THEME_PROGRESS_FILL"): THEME_PROGRESS_FILL = _hex_to_color(p.THEME_PROGRESS_FILL)
	if p.has("THEME_WARN_ORANGE"): THEME_WARN_ORANGE = _hex_to_color(p.THEME_WARN_ORANGE)
	if p.has("THEME_WHITE"): THEME_WHITE = _hex_to_color(p.THEME_WHITE)
	var rc: Dictionary = p.get("rarity_colors", {})
	for key in rc:
		if RARITY_COLORS.has(key): RARITY_COLORS[key] = _hex_to_color(rc[key])
	var rbc: Dictionary = p.get("rarity_badge_colors", {})
	for key in rbc:
		if RARITY_BADGE_COLORS.has(key): RARITY_BADGE_COLORS[key] = _hex_to_color(rbc[key])

## 金白深灰主题预设（DESIGN.md 定稿）：按语义把 THEME_* 覆盖到 COLOR_*，组件零改动。
## 映射登记在 docs/shadcn-mapping.md；切换 = 改 style-config.json 的 active_theme。
static func _apply_theme_preset() -> void:
	# 底 / 面板 / 遮罩
	COLOR_PANEL_BG = Color(THEME_BG, 0.8)
	COLOR_PANEL_BORDER = Color(THEME_GRAY_MID, 0.5)
	COLOR_BAR_BG = Color(THEME_BG, 0.9)
	COLOR_BAR_TRACK = Color(THEME_BG, 0.9)
	COLOR_HP_BG = Color(THEME_BG, 0.85)
	COLOR_OVERLAY = Color(0, 0, 0, 0.55)
	COLOR_DRAG_PREVIEW_BG = Color(THEME_BG, 0.92)
	COLOR_SKILL_SLOT_BG = THEME_GRAY_MID
	COLOR_SKILL_SLOT_BORDER = THEME_GOLD
	# 槽位 / 边框
	COLOR_BAR_BORDER = THEME_GOLD
	COLOR_SLOT_BG = THEME_GRAY_MID
	COLOR_SLOT_BORDER = THEME_GRAY_MID
	COLOR_SLOT_HOVER_BG = Color(THEME_GRAY_MID, 0.85)
	COLOR_SLOT_HOVER_BORDER = THEME_GOLD
	COLOR_ITEM_BG = Color(THEME_BG, 0.7)
	COLOR_ITEM_BORDER = THEME_GOLD
	COLOR_DRAG_OVER_BG = Color(THEME_GOLD, 0.18)
	COLOR_DRAG_OVER_BORDER = THEME_GOLD
	COLOR_EQUIP_SLOT_BG = THEME_GRAY_MID
	COLOR_EQUIP_SLOT_BORDER = THEME_GRAY_MID
	COLOR_EQUIP_EQUIPPED_BG = Color(THEME_GOLD, 0.18)
	COLOR_EQUIP_EQUIPPED_BORDER = THEME_GOLD
	COLOR_EQUIP_LOCKED_BG = Color(THEME_GRAY_MID, 0.5)
	COLOR_EQUIP_LOCKED_BORDER = Color(THEME_GRAY_MID, 0.8)
	COLOR_EQUIP_LOCK_OVERLAY = Color(0, 0, 0, 0.62)
	# 文本层级
	COLOR_TEXT = THEME_WHITE
	COLOR_DIM_TEXT = THEME_GRAY_LIGHT
	COLOR_MUTED = Color(THEME_GRAY_MID, 0.9)
	COLOR_NOTICE = THEME_GOLD
	COLOR_STATUS = THEME_GOLD
	COLOR_AMMO = THEME_WHITE
	COLOR_KILL = THEME_GOLD
	COLOR_TITLE_TEXT = THEME_WHITE
	COLOR_STACK_TEXT = THEME_WHITE
	COLOR_KEY_HINT = THEME_GRAY_LIGHT
	COLOR_DEATH_TITLE = THEME_DANGER_RED
	COLOR_DEATH_HINT = THEME_GRAY_LIGHT
	COLOR_ZERO_TEXT = THEME_DANGER_RED
	COLOR_RARITY_TEXT = Color(THEME_BG, 1.0)
	# 状态条（状态色专属）
	COLOR_HP_HIGH = THEME_HP_GREEN
	COLOR_HP_MID = THEME_WARN_ORANGE
	COLOR_HP_LOW = THEME_DANGER_RED
	COLOR_MP_FILL = THEME_MP_BLUE
	COLOR_STAMINA_FILL = THEME_GOLD
	COLOR_EXP_FILL = THEME_GOLD
	# 准星 / 命中
	COLOR_CROSSHAIR = THEME_WHITE
	COLOR_HITMARKER = THEME_WHITE
	COLOR_DMG_FLASH = Color(THEME_DANGER_RED, 0.0)
	# 浮窗：保持旧版纯白底（COLOR_TT_* 默认值，主题预设不覆盖）
	# 徽章（金色徽章对齐主题，改造/附魔保留语义色）
	COLOR_BADGE_GOLD_BG = Color(THEME_GOLD, 0.92)
	COLOR_BADGE_GOLD_TEXT = Color(THEME_BG, 1.0)
