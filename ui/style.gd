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
const COLOR_EQUIP_SLOT_BG := Color(0.24, 0.204, 0.169)
const COLOR_EQUIP_SLOT_BORDER := Color(0.353, 0.302, 0.247)
const COLOR_EQUIP_EQUIPPED_BG := Color(0.145, 0.13, 0.11)
const COLOR_EQUIP_EQUIPPED_BORDER := Color(0.55, 0.55, 0.55)
const COLOR_EQUIP_LOCKED_BG := Color(0.18, 0.18, 0.18, 0.72)
const COLOR_EQUIP_LOCKED_BORDER := Color(0.27, 0.27, 0.27)
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
const COLOR_DMG_FLASH := Color(0.8, 0, 0, 0)
const COLOR_TRANSPARENT := Color(0, 0, 0, 0)

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
const COLOR_TT_SECTION_BORDER := Color(0, 0, 0, 0.12)
const COLOR_TT_CRAFT_POS := Color(0, 0.6, 0)
const COLOR_TT_CRAFT_NEG := Color(0.85, 0, 0)
const COLOR_TT_ENCHANT_NAME := Color(0.75, 0.63, 0.38)
const COLOR_BADGE_GOLD_BG := Color(1.0, 0.84, 0.0, 0.92)
const COLOR_BADGE_GOLD_TEXT := Color(0.1, 0.1, 0.18)
const COLOR_BADGE_CRAFT_BG := Color(0.42, 0.62, 0.9, 0.92)
const COLOR_BADGE_CRAFT_TEXT := Color(0.95, 0.97, 1.0)
const COLOR_BADGE_ENCHANT_BG := Color(0.66, 0.42, 0.85, 0.92)
const COLOR_BADGE_ENCHANT_TEXT := Color(0.98, 0.95, 1.0)

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
## 装备槽稀有度竖排徽章底色（半透明，对齐旧版 .slot-rarity.rarity-*）
const RARITY_BADGE_COLORS := {
	"common": Color(0.71, 0.71, 0.71, 0.85),
	"uncommon": Color(0.48, 0.78, 0.48, 0.7),
	"rare": Color(0.48, 0.62, 0.78, 0.7),
	"epic": Color(0.71, 0.48, 0.78, 0.7),
	"mythic": Color(0.9, 0.59, 0.24, 0.78),
	"legendary": Color(0.84, 0.24, 0.22, 0.8),
}

# ---------- v2 全境封锁风色板（DESIGN.md Token，未启用） ----------
# 切换时用下方色板整体替换上方旧 2D 暗金色板即可，HUD/背包代码零改动。
const V2_BG_SCENE := Color(0.039, 0.055, 0.086)       # #0A0E16 深蓝黑底
const V2_ACCENT_CYAN := Color(0.310, 0.765, 0.969)    # #4FC3F7 科技/战术主强调
const V2_ACCENT_GOLD := Color(1.0, 0.847, 0.290)      # #FFD84A 游戏次强调
const V2_HP_GREEN := Color(0.498, 0.824, 0.416)       # #7FD26A 生命
const V2_WARN_ORANGE := Color(0.878, 0.663, 0.310)    # #E0A94F 警告
const V2_DANGER_RED := Color(0.851, 0.357, 0.290)     # #D95B4A 危险
const V2_MP_BLUE := Color(0.353, 0.561, 0.878)        # #5A8FE0 魔力
const V2_TEXT_PRIMARY := Color(0.910, 0.894, 0.847)   # #E8E4D8 主文本
const V2_TEXT_SECONDARY := Color(0.667, 0.690, 0.729) # #AAB0BA 次级文本
const V2_TEXT_WEAK := Color(0.420, 0.447, 0.502)      # #6B7280 弱化文本

# ---------- 字体 ----------

static func make_font() -> SystemFont:
	var f := SystemFont.new()
	f.font_names = PackedStringArray(["Microsoft YaHei", "SimHei", "Noto Sans CJK SC"])
	return f

## emoji 回退字体（旧版图标加载失败时显示 item.icon 字符）
static func make_emoji_font() -> SystemFont:
	var f := SystemFont.new()
	f.font_names = PackedStringArray(["Segoe UI Emoji", "Noto Color Emoji", "Apple Color Emoji"])
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
