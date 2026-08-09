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

## NPC 预设（旧版 data/game-config.json npcs 对齐）
const NPCS := {
	"shop_mouse_king": {
		"id": "shop_mouse_king",
		"name": "小鼠大王",
		"npc_type": "shop",
		"portrait": "res://assets/ui/npc/npc_portrait.png",
		"shop_id": "main",
		"greetings": [
			"你好，冒险者！欢迎来到无尽轮回。",
			"今天的天空格外晴朗呢。",
			"新鲜货物刚到，快来看看！",
			"如果你需要强化装备，我可以帮你。",
		],
	},
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
const CRAFT_CONFIG_PATH := "res://assets/data/craft-config.json"

## 改造（craft-config.json 全量 17 把武器，运行时加载，避免手抄遗漏）
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
	# 旧版 gun-ammo.js：所有 weapon_ranged/melee/shield 都可放入，无配置再提示不可改造
	var cat := String(item.get("category", ""))
	return cat == "weapon_melee" or cat == "weapon_ranged" or cat == "weapon_shield"

static func get_craft_config(weapon_id: String) -> Dictionary:
	return _load_craft_config().get(weapon_id, {})

static func has_craft_config(item: Dictionary) -> bool:
	return not get_craft_config(String(item.get("weaponId", ""))).is_empty()

static var _craft_cache: Dictionary = {}
static var _craft_defaults: Dictionary = {}

static func _load_craft_config() -> Dictionary:
	if _craft_cache.is_empty() and FileAccess.file_exists(CRAFT_CONFIG_PATH):
		var f := FileAccess.open(CRAFT_CONFIG_PATH, FileAccess.READ)
		if f != null:
			var parsed = JSON.parse_string(f.get_as_text())
			f.close()
			if typeof(parsed) == TYPE_DICTIONARY:
				_craft_cache = parsed
				if _craft_defaults.is_empty():
					_craft_defaults = parsed.duplicate(true)
	return _craft_cache

static func craft_config_for(item: Dictionary) -> Dictionary:
	return get_craft_config(String(item.get("weaponId", "")))

## 布局编辑落盘（旧版 CraftSystem._persistCraftConfig 迁移：写回 assets/data/craft-config.json）
static func update_craft_layout(weapon_id: String, slots: Array) -> void:
	_load_craft_config()
	if _craft_cache.has(weapon_id):
		_craft_cache[weapon_id]["slots"] = slots
		_save_craft_config()

static func reset_craft_layout(weapon_id: String) -> void:
	_load_craft_config()
	if _craft_defaults.has(weapon_id) and _craft_cache.has(weapon_id):
		_craft_cache[weapon_id]["slots"] = _craft_defaults[weapon_id]["slots"].duplicate(true)
		_save_craft_config()

static func _save_craft_config() -> void:
	var f := FileAccess.open(CRAFT_CONFIG_PATH, FileAccess.WRITE)
	if f != null:
		f.store_string(JSON.stringify(_craft_cache, "\t"))
		f.close()

## 旧版图标路径（assets/icons/craft/x.png 等）→ 本地 res:// 路径；不存在返回空
static func map_icon_path(path: String) -> String:
	if path == "":
		return ""
	var local := path
	if path.begins_with("assets/"):
		local = "res://assets/" + path.trim_prefix("assets/")
	elif not path.begins_with("res://"):
		return ""
	if ResourceLoader.exists(local):
		return local
	return ""

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
