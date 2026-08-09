extends RefCounted
## UI 风格集中定义（换肤只改本文件）
## 当前沿用旧 2D 版深棕/暗金基调；后续接 moodboard（全境封锁 x 暗金六边形）时
## 只需替换这里的色板 / 字体 / 圆角，HUD 代码零改动。

# ---------- 基础色板 ----------
const COLOR_BAR_BG := Color(0.16, 0.145, 0.125, 0.94)
const COLOR_BAR_BORDER := Color(0.353, 0.302, 0.247)
const COLOR_SLOT_BG := Color(0.239, 0.204, 0.169)
const COLOR_SLOT_BORDER := Color(0.353, 0.302, 0.247)
const COLOR_SLOT_HOVER_BG := Color(0.29, 0.247, 0.208)
const COLOR_SLOT_HOVER_BORDER := Color(0.545, 0.478, 0.408)
const COLOR_ITEM_BG := Color(0.239, 0.29, 0.208)
const COLOR_ITEM_BORDER := Color(0.478, 0.604, 0.416)
const COLOR_DRAG_OVER_BG := Color(0.29, 0.25, 0.208)
const COLOR_DRAG_OVER_BORDER := Color(0.831, 0.773, 0.659)
const COLOR_PANEL_BG := Color(0.11, 0.10, 0.085, 0.0)
const COLOR_PANEL_BORDER := Color(0.55, 0.46, 0.34)
const COLOR_OVERLAY := Color(0, 0, 0, 0.35)
const COLOR_TEXT := Color(0.831, 0.773, 0.659)
const COLOR_DIM_TEXT := Color(0.545, 0.478, 0.408)
const COLOR_NOTICE := Color(0.98, 0.75, 0.4)
const COLOR_STATUS := Color(0.98, 0.75, 0.4)
const COLOR_AMMO := Color(0.92, 0.92, 0.96)
const COLOR_KILL := Color(0.96, 0.9, 0.7)
const COLOR_HP_BG := Color(0.05, 0.06, 0.10, 0.72)
const COLOR_HP_HIGH := Color(0.5, 0.82, 0.42)
const COLOR_HP_MID := Color(0.88, 0.66, 0.31)
const COLOR_HP_LOW := Color(0.85, 0.36, 0.29)
const COLOR_DEATH_TITLE := Color(0.95, 0.4, 0.35)
const COLOR_DEATH_HINT := Color(0.85, 0.85, 0.9)
const COLOR_CROSSHAIR := Color(0.95, 0.95, 0.9)
const COLOR_HITMARKER := Color(0.98, 0.98, 0.95)

# ---------- 浮窗（白底，复刻旧版 tt-main） ----------
const COLOR_TT_BG := Color(0.96, 0.95, 0.93)
const COLOR_TT_BORDER := Color(0, 0, 0, 0.25)
const COLOR_TT_NAME := Color(0.16, 0.145, 0.125)
const COLOR_TT_TYPE := Color(0.29, 0.247, 0.208)
const COLOR_TT_VAL := Color(0.16, 0.145, 0.125)
const COLOR_TT_POS := Color(0.165, 0.478, 0.165)
const COLOR_TT_DESC := Color(0.42, 0.365, 0.31)
const COLOR_TT_CLOSE_BG := Color(0.78, 0.2, 0.2, 0.8)
const COLOR_TT_CLOSE_HOVER := Color(0.86, 0.27, 0.27)

# ---------- 稀有度（对齐旧版 src/config/rarity.js） ----------
const RARITY_LABELS := {
	"common": "普通",
	"uncommon": "优质",
	"rare": "稀有",
	"epic": "史诗",
	"mythic": "神话",
	"legendary": "传说",
}
const RARITY_COLORS := {
	"common": Color(0.7529, 0.7529, 0.7529),
	"uncommon": Color(0.4784, 1.0, 0.4784),
	"rare": Color(0.4784, 0.6039, 1.0),
	"epic": Color(0.7765, 0.4784, 1.0),
	"mythic": Color(0.9020, 0.6039, 0.2353),
	"legendary": Color(0.8784, 0.2902, 0.2275),
}

# ---------- 字体 ----------

static func make_font() -> SystemFont:
	var f := SystemFont.new()
	f.font_names = PackedStringArray(["Microsoft YaHei", "SimHei", "Noto Sans CJK SC"])
	return f

static func make_theme() -> Theme:
	var t := Theme.new()
	t.default_font = make_font()
	t.default_font_size = 13
	return t

static func make_style(bg: Color, border: Color, radius := 8, border_w := 2) -> StyleBoxFlat:
	var sb := StyleBoxFlat.new()
	sb.bg_color = bg
	sb.border_color = border
	sb.set_border_width_all(border_w)
	sb.set_corner_radius_all(radius)
	return sb

static func rarity_label(key: String) -> String:
	return String(RARITY_LABELS.get(key, key))

static func rarity_color(key: String) -> Color:
	return RARITY_COLORS.get(key, Color.WHITE)
