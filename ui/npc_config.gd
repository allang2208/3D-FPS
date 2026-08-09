extends RefCounted
## NPC 面板配置（UI 迁移线）：旧版 npc-dialogue.js 各选项子面板的纯数据层。
## 数值与旧版 data/craft-config.json、src/config/enchant-config.js、quest-system.js 对齐；
## 只做只读配置，改动先改这里。

const Style := preload("res://ui/style.gd")

const RARITY_ORDER: Array = ["common", "uncommon", "rare", "epic", "mythic", "legendary"]
const RARITY_STANDARD_PRICE := {
	"common": 100, "uncommon": 200, "rare": 400,
	"epic": 800, "mythic": 1600, "legendary": 3200,
}

## 商店目录：shopId -> 物品 id 列表（运行时按 item_db.has_item 过滤缺失）
const SHOP_CATALOGS := {
	"main": [
		"rusty_sword", "knights_sword", "rune_sword", "night_flame_sword",
		"small_shield", "g18_pistol", "m416", "qbz191", "pkm",
		"hp_potion", "mp_potion", "enhancement_stone", "reforge_ticket",
		"enchant_scroll_heavy", "enchant_scroll_sharp",
		"enchant_scroll_tarantula", "enchant_scroll_skeleton",
	],
	"blacksmith": [
		"rusty_sword", "knights_sword", "rune_sword", "small_shield",
		"g18_pistol", "m416", "enhancement_stone", "reforge_ticket",
		"enchant_scroll_heavy", "enchant_scroll_sharp",
	],
}

## 强化（enhance-system.js 对齐）：武器（含盾）15 级，其余 10 级
const ENHANCE_MAX_LEVEL := 15
const ENHANCE_NON_WEAPON_MAX_LEVEL := 10
const ENHANCE_BASE_COST := 100
const ENHANCE_COST_GROWTH := 1.5
const ENHANCE_STONE_ID := "enhancement_stone"

## 改造（craft-config.json 对齐，裁剪到 Godot 已有武器；slot 布局坐标省略，仅保留 mod 逻辑）
const CRAFT_CONFIG := {
	"weapon2": {
		"slots": [
			{"id": "blade", "name": "剑刃"},
			{"id": "guard", "name": "护手"},
			{"id": "grip", "name": "握把"},
		],
		"options": {
			"blade": [
				{"id": "light_blade", "name": "轻量化剑刃", "desc": "减少攻击间隔 50ms", "effects": {"attackIntervalDelta": -50}},
				{"id": "hardened_edge", "name": "淬火硬化刃口", "desc": "增加 10% 暴击率", "effects": {"critChancePercent": 0.1}},
				{"id": "heavy_blunt", "name": "厚重钝化", "desc": "增加 20% 防御穿透", "effects": {"armorPenetrationPercent": 0.2}},
				{"id": "sharpened_edge", "name": "精细研磨（开刃）", "desc": "增加 5% 伤害", "effects": {"damagePercent": 0.05}},
			],
			"guard": [
				{"id": "small_disc_guard", "name": "小型圆盘护手", "desc": "减少攻击间隔 50ms", "effects": {"attackIntervalDelta": -50}},
				{"id": "wide_cross_guard", "name": "宽十字护手", "desc": "装备时获得次级格挡：近战攻击 50% 概率减伤", "effects": {"secondaryBlock": true}},
				{"id": "no_guard", "name": "无护手", "desc": "攻击间隔-100ms，体力消耗-5，防御力-25%", "effects": {"attackIntervalDelta": -100, "staminaCostDelta": -5, "defensePercent": -0.25}},
			],
			"grip": [
				{"id": "wrapped_long_grip", "name": "缠绳加长柄", "desc": "减少 5 点攻击和技能体力消耗", "effects": {"staminaCostDelta": -5, "skillStaminaCostDelta": -5}},
				{"id": "short_compact_grip", "name": "短柄紧凑型握把", "desc": "减少攻击间隔 50ms", "effects": {"attackIntervalDelta": -50}},
			],
		},
	},
	"weapon4": {
		"slots": [
			{"id": "blade", "name": "剑刃"},
			{"id": "grip", "name": "握把"},
		],
		"options": {
			"blade": [
				{"id": "rune_restructure", "name": "符文重构", "desc": "右键特殊攻击额外生成 2 把魔法剑", "effects": {"runeRestructureCount": 2}},
				{"id": "sharp_rune", "name": "锋利符文", "desc": "魔法防御穿透 20%", "effects": {"magicPenetrationPercent": 0.2}},
				{"id": "destruction_rune", "name": "毁灭符文", "desc": "魔法剑击中附加 2 层魔力易伤", "effects": {"magicVulnerabilityOnHit": true, "magicVulnerabilityStacks": 2}},
			],
			"grip": [
				{"id": "alloy_grip", "name": "合金", "desc": "施法前摇缩短 25%", "effects": {"castSpeedPercent": 0.25}},
				{"id": "sandalwood_grip", "name": "檀木", "desc": "施法后 5 秒加速效果", "effects": {"castHasteDuration": 5000, "castHasteStacks": 1}},
			],
		},
	},
	"weapon7": {
		"slots": [
			{"id": "barrel", "name": "枪管"},
			{"id": "trigger", "name": "扳机"},
			{"id": "magazine", "name": "弹匣"},
		],
		"options": {
			"barrel": [
				{"id": "longshot_barrel", "name": "远射枪管", "desc": "射程+300px，散布更集中", "effects": {"rangeDelta": 300, "shotSpreadDelta": -1}},
				{"id": "cqb_barrel", "name": "近战短管", "desc": "移动速度+5%，散布增大", "effects": {"moveSpeedPercent": 0.05, "shotSpreadDelta": 1}},
			],
			"trigger": [
				{"id": "auto_trigger", "name": "全自动扳机", "desc": "切换全自动射击模式", "effects": {"fireModeOverride": "fullAuto", "attackIntervalDelta": -100}},
				{"id": "lightweight_trigger", "name": "轻量化快速扳机", "desc": "攻击间隔-100ms，换弹-500ms", "effects": {"attackIntervalDelta": -100, "reloadTimeDelta": -500}},
			],
			"magazine": [
				{"id": "light_extended_mag", "name": "轻型扩容弹匣", "desc": "备弹+6", "effects": {"magazineDelta": 6}},
				{"id": "long_extended_mag", "name": "长扩容弹匣", "desc": "备弹+12，换弹+300ms", "effects": {"magazineDelta": 12, "reloadTimeDelta": 300}},
			],
		},
	},
	"weapon9": {
		"slots": [
			{"id": "trigger", "name": "扳机"},
			{"id": "magazine", "name": "弹匣"},
		],
		"options": {
			"trigger": [
				{"id": "auto_trigger", "name": "全自动扳机", "desc": "切换全自动射击模式", "effects": {"fireModeOverride": "fullAuto", "attackIntervalDelta": -100}},
				{"id": "lightweight_trigger", "name": "轻量化快速扳机", "desc": "攻击间隔-100ms，换弹-500ms", "effects": {"attackIntervalDelta": -100, "reloadTimeDelta": -500}},
			],
			"magazine": [
				{"id": "light_extended_mag", "name": "轻型扩容弹匣", "desc": "备弹+6", "effects": {"magazineDelta": 6}},
				{"id": "quick_mag", "name": "快拔弹匣", "desc": "换弹-500ms，移动速度+3%", "effects": {"reloadTimeDelta": -500, "moveSpeedPercent": 0.03}},
			],
		},
	},
}
const REFORGE_TICKET_ID := "reforge_ticket"

## 附魔（enchant-config.js 对齐）
const ENCHANT_SCROLLS := {
	"heavy": {
		"id": "heavy", "name": "沉重", "grade": "common", "type": "prefix", "cost": 100,
		"restrictions": {"weaponTypes": ["sword"]},
		"effects": {"damagePercent": 0.60, "attackIntervalMul": 1.35},
		"desc": "攻击力增加 60%，攻击速度降低约 36%",
		"icon_fallback": "⚔️",
	},
	"sharp": {
		"id": "sharp", "name": "锋利的", "grade": "common", "type": "prefix", "cost": 100,
		"restrictions": {"weaponTypes": ["sword"]},
		"effects": {"critRate": 0.50},
		"desc": "暴击率增加 50%",
		"icon_fallback": "⚔️",
	},
	"tarantula": {
		"id": "tarantula", "name": "狼蛛", "grade": "uncommon", "type": "suffix", "cost": 200,
		"restrictions": {},
		"effects": {"poisonOnHit": true, "poisonStacks": 1},
		"desc": "每次攻击给敌人叠加一层中毒效果",
		"icon_fallback": "🕷️",
	},
	"skeletonArcher": {
		"id": "skeletonArcher", "name": "骷髅射手", "grade": "rare", "type": "suffix", "cost": 400,
		"restrictions": {"weaponTypes": ["pistol", "pkm", "akm", "m416", "qbz191", "qjb201", "shotgun"]},
		"effects": {"piercingBonus": 2},
		"desc": "穿透目标 2",
		"icon_fallback": "🦴",
	},
}
const MAGIC_DUST_ID := "magic_dust"
const SCROLL_ITEM_IDS := {
	"heavy": "enchant_scroll_heavy",
	"sharp": "enchant_scroll_sharp",
	"tarantula": "enchant_scroll_tarantula",
	"skeletonArcher": "enchant_scroll_skeleton",
}

## 任务（quest-system.js 对齐）
const QUESTS := {
	"explore_rift_1": {
		"id": "explore_rift_1",
		"name": "探索时空裂隙",
		"type": "主线任务",
		"desc": "根据线索，近期发现不同世界中出现了时空乱流和时空不稳定的裂隙，前往最近发生情况的181号世界，找到发生时空裂隙的地方，收集线索调查。",
		"objectives": [
			{"id": "rift_1", "text": "完成三个时空裂隙的线索收集", "current": 0, "target": 3},
			{"id": "evacuate", "text": "成功从 181 世界中撤离", "current": 0, "target": 1},
		],
		"rewards": [
			{"type": "level", "text": "提升一级"},
			{"type": "gold", "text": "500 金币"},
			{"type": "weapon", "text": "随机优质武器"},
		],
		"scene": "scene2",
	},
}

## 祭品合成：同稀有度两两合成 -> 更高一级（传说对 -> 随机新传说）
const FUSION_CAPACITY := 20

static func rarity_label(rarity: String) -> String:
	return Style.rarity_label(rarity)

static func rarity_color(rarity: String) -> Color:
	return Style.rarity_color(rarity)

static func rarity_rank(rarity: String) -> int:
	return RARITY_ORDER.find(rarity)

static func standard_price(def: Dictionary) -> int:
	if int(def.get("price", 0)) > 0:
		return int(def["price"])
	return int(RARITY_STANDARD_PRICE.get(String(def.get("rarity", "common")), 100))

static func enhance_cost(level: int) -> int:
	return int(ENHANCE_BASE_COST * pow(ENHANCE_COST_GROWTH, level))

static func enhance_max_level(item: Dictionary) -> int:
	var cat := String(item.get("category", ""))
	var is_weapon := cat.begins_with("weapon") or String(item.get("weaponType", "")) != ""
	return ENHANCE_MAX_LEVEL if is_weapon else ENHANCE_NON_WEAPON_MAX_LEVEL

static func is_craftable(item: Dictionary) -> bool:
	return CRAFT_CONFIG.has(String(item.get("weaponId", "")))

static func craft_config_for(item: Dictionary) -> Dictionary:
	return CRAFT_CONFIG.get(String(item.get("weaponId", "")), {})

static func get_scroll(scroll_id: String) -> Dictionary:
	return ENCHANT_SCROLLS.get(scroll_id, {})

static func can_enchant(item: Dictionary, scroll_id: String) -> bool:
	var scroll := get_scroll(scroll_id)
	if scroll.is_empty() or item.is_empty():
		return false
	var restrictions: Dictionary = scroll.get("restrictions", {})
	if restrictions.is_empty():
		return true
	var weapon_types: Array = restrictions.get("weaponTypes", [])
	if weapon_types.is_empty():
		return true
	var item_type := String(item.get("weaponType", item.get("category", "")))
	return weapon_types.has(item_type)

static func scroll_conversion_reward(scroll_id: String) -> int:
	var scroll := get_scroll(scroll_id)
	if scroll.is_empty():
		return 0
	return int(scroll.get("cost", 0)) / 2
