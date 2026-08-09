extends RefCounted
## UI 风格集中定义（换肤只改本文件）
## 定稿方向（DESIGN.md）：金主色 + 白信息 + 深灰底（下方 THEME_* 块）。
## 切换时用 THEME_* 色板整体替换上方旧 2D 暗金 COLOR_*，HUD/背包代码零改动。

# ---------- 基础色板（旧版 2D 暗金棕，精确对齐 style.css / game-style.css） ----------
const COLOR_BAR_BG := Color(0.1647, 0.1451, 0.1255, 0.9)       # rgba(42,37,32,0.9)
const COLOR_BAR_BORDER := Color(0.3529, 0.3020, 0.2471)        # #5a4d3f
const COLOR_SLOT_BG := Color(0.2392, 0.2039, 0.1686)           # #3d342b
const COLOR_SLOT_BORDER := Color(0.3529, 0.3020, 0.2471)       # #5a4d3f
const COLOR_SLOT_HOVER_BG := Color(0.2902, 0.2471, 0.2078)     # #4a3f35
const COLOR_SLOT_HOVER_BORDER := Color(0.5412, 0.4902, 0.4196) # #8a7d6b
const COLOR_ITEM_BG := Color(0.2392, 0.2902, 0.2078)           # #3d4a35（占用）
const COLOR_ITEM_BORDER := Color(0.4784, 0.6039, 0.4157)       # #7a9a6a（占用）
const COLOR_DRAG_OVER_BG := Color(0.2902, 0.2471, 0.2078)      # #4a3f35
const COLOR_DRAG_OVER_BORDER := Color(0.8314, 0.7725, 0.6627)  # #d4c5a9
const COLOR_EQUIP_SLOT_BG := Color(0.2392, 0.2039, 0.1686)     # #3d342b
const COLOR_EQUIP_SLOT_BORDER := Color(0.3529, 0.3020, 0.2471) # #5a4d3f
const COLOR_EQUIP_EQUIPPED_BG := Color(0.3137, 0.3137, 0.3137, 0.95)   # rgba(80,80,80,0.95)
const COLOR_EQUIP_EQUIPPED_BORDER := Color(0.4706, 0.4706, 0.4706, 0.7) # rgba(120,120,120,0.7)
const COLOR_EQUIP_LOCKED_BG := Color(0.4706, 0.4706, 0.4706, 0.6)      # rgba(120,120,120,0.6)
const COLOR_EQUIP_LOCKED_BORDER := Color(0.2667, 0.2667, 0.2667)       # #444
const COLOR_PANEL_BG := Color(0.0784, 0.0784, 0.0980, 0.8)     # rgba(20,20,25,0.8)
const COLOR_PANEL_BORDER := Color(0.2353, 0.2353, 0.2745, 0.5) # rgba(60,60,70,0.5)
const COLOR_OVERLAY := Color(0, 0, 0, 0.3)                      # rgba(0,0,0,0.3)
const COLOR_TEXT := Color(0.8314, 0.7725, 0.6627)               # #d4c5a9
const COLOR_DIM_TEXT := Color(0.5412, 0.4902, 0.4196)           # #8a7d6b
const COLOR_MUTED := Color(0.4196, 0.3647, 0.3098)              # #6b5d4f
const COLOR_NOTICE := Color(0.8314, 0.7725, 0.6627)             # #d4c5a9
const COLOR_STATUS := Color(0.8314, 0.7725, 0.6627)             # #d4c5a9
const COLOR_AMMO := Color(0.8314, 0.7725, 0.6627)               # #d4c5a9
const COLOR_KILL := Color(0.8314, 0.7725, 0.6627)               # #d4c5a9
const COLOR_HP_BG := Color(0.1647, 0.1451, 0.1255, 0.85)        # rgba(42,37,32,0.85) 顶栏底
const COLOR_HP_HIGH := Color(0.6275, 0.3765, 0.3765)            # #a06060（旧版红棕血条）
const COLOR_HP_MID := Color(0.5412, 0.2902, 0.2902)            # #8a4a4a
const COLOR_HP_LOW := Color(0.4784, 0.2275, 0.2275)            # #7a3a3a
const COLOR_DEATH_TITLE := Color(0.95, 0.4, 0.35)
const COLOR_DEATH_HINT := Color(0.8314, 0.7725, 0.6627)         # #d4c5a9
const COLOR_CROSSHAIR := Color(0.95, 0.95, 0.9)
const COLOR_HITMARKER := Color(0.98, 0.98, 0.95)
const COLOR_DMG_FLASH := Color(0.8, 0, 0, 0)
const COLOR_TRANSPARENT := Color(0, 0, 0, 0)
const COLOR_WHITE := Color(1, 1, 1)
const COLOR_BLACK := Color(0, 0, 0)
const COLOR_TITLE_TEXT := Color(0.8314, 0.7725, 0.6627)         # #d4c5a9
const COLOR_STACK_TEXT := Color(0.8314, 0.7725, 0.6627)         # #d4c5a9
const COLOR_KEY_HINT := Color(1, 1, 1)                           # #ffffff（旧版快捷栏键位）
const COLOR_ZERO_TEXT := Color(0.95, 0.35, 0.32)
const COLOR_RARITY_TEXT := Color(0.1, 0.1, 0.1)
const COLOR_EQUIP_LOCK_OVERLAY := Color(0.12, 0.12, 0.12, 0.62)
const COLOR_DRAG_PREVIEW_BG := Color(0.2, 0.18, 0.15, 0.92)

# ---------- 浮窗（白底，复刻旧版 tt-main） ----------
const COLOR_TT_BG := Color(0.96, 0.96, 0.96)                    # 旧版白底浮窗渐变近似
const COLOR_TT_BORDER := Color(0, 0, 0, 0.2)                    # rgba(0,0,0,0.2)
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

# ---------- 定稿金色板（DESIGN.md Token，未启用） ----------
# 全境封锁 UI 改进情绪板定稿：金主色 + 白信息 + 深灰底。
# 切换时用下方色板整体替换上方旧 2D 暗金 COLOR_*，HUD/背包代码零改动。
const THEME_BG := Color(0.0588, 0.0588, 0.0627)          # #0F0F10 深灰黑底
const THEME_GOLD := Color(0.8314, 0.6863, 0.2157)        # #D4AF37 核心强调
const THEME_WHITE := Color(1, 1, 1)                      # #FFFFFF 主信息文本
const THEME_GRAY_LIGHT := Color(0.7098, 0.7098, 0.7098)  # #B5B5B5 次级文本/禁用字
const THEME_GRAY_MID := Color(0.2275, 0.2275, 0.2353)    # #3A3A3C 边框/分隔线/按钮底
const THEME_HP_GREEN := Color(0.498, 0.824, 0.416)       # #7FD26A 生命（状态）
const THEME_WARN_ORANGE := Color(0.878, 0.663, 0.310)    # #E0A94F 警告（状态）
const THEME_DANGER_RED := Color(0.851, 0.357, 0.290)     # #D95B4A 危险（状态）
const THEME_MP_BLUE := Color(0.353, 0.561, 0.878)        # #5A8FE0 魔力（状态）
# 按钮三态 / 进度条 / 分隔线（DESIGN.md 第 5 节）
const THEME_BTN_BG := Color(0.2275, 0.2275, 0.2353)      # 默认底（同 GRAY_MID）
const THEME_BTN_HOVER_BG := Color(0.8314, 0.6863, 0.2157) # 悬停金底
const THEME_BTN_DISABLED_BG := Color(0.2275, 0.2275, 0.2353) # 禁用底
const THEME_BTN_DISABLED_TEXT := Color(0.7098, 0.7098, 0.7098) # 禁用字
const THEME_PROGRESS_FILL := Color(0.8314, 0.6863, 0.2157) # 进度条金填充
const THEME_DIVIDER := Color(0.2275, 0.2275, 0.2353)     # 细分隔线
const THEME_DIVIDER_ACCENT := Color(0.8314, 0.6863, 0.2157, 0.6) # 金色强调分隔线

# ---------- 字体 ----------

## 黑体字重阶梯（DESIGN.md：标题 Heavy / 副标题 Bold / 正文 Regular）
static func make_font(weight := 400) -> SystemFont:
	var f := SystemFont.new()
	f.font_names = PackedStringArray(["Source Han Sans SC", "Noto Sans CJK SC", "Microsoft YaHei", "SimHei"])
	f.font_weight = weight
	return f

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
