extends RefCounted
const Rules := preload("res://ui/item_rules.gd")
## 物品库：消耗品定义 + 加载旧版 data/equipment.json（125 件装备）
## 字段沿用旧版：id / name / type / icon / category / rarity / stack / stack_max /
##               stats / useEffect / useCooldown / desc / equipSlot / attack / ammoConfig ...

const HP_POTION_ICON := "res://assets/ui/icons/health_potion.png"
const MP_POTION_ICON := "res://assets/ui/icons/mana_potion.png"
const EQUIPMENT_JSON := "res://assets/data/equipment.json"
const EQUIP_ICON_DIRS := [
	"res://assets/ui/icons/equip/",
	"res://assets/ui/icons/skills/",
	"res://assets/ui/icons/",
]

var _defs := {
	"silver_ore": {"name":"银矿", "type":"材料", "category":"material", "rarity":"common", "stack_max":999,
		"icon":"res://assets/environment/silver_vein_v1/silver_ore_icon.png", "desc":"矿镐采集的含银矿石，深色围岩中分布银白矿带，可用于后续冶炼制造。"},
	"gold_ore": {"name":"金矿", "type":"材料", "category":"material", "rarity":"common", "stack_max":999,
		"icon":"res://assets/environment/gold_vein_v1/gold_ore_icon.png", "desc":"矿镐采集的含金矿石，石英脉中分布金黄色矿粒，可用于后续冶炼制造。"},
	"copper_ore": {"name":"铜矿", "type":"材料", "category":"material", "rarity":"common", "stack_max":999,
		"icon":"res://assets/environment/copper_vein_v1/copper_ore_icon.png", "desc":"矿镐采集的含铜矿石，赤铜色矿带与青绿色风化矿斑交织，可用于后续冶炼制造。"},
	"iron_ore": {"name":"铁矿", "type":"材料", "category":"material", "rarity":"common", "stack_max":999,
		"icon":"res://assets/environment/iron_vein_v1/iron_ore_icon.png", "desc":"用矿镐从铁矿脉中采集的含铁矿石，可用于后续冶炼与制造。"},
	"wood": {"name":"木材", "type":"材料", "category":"material", "rarity":"common", "stack_max":999,
		"icon":"res://assets/ui/building/floor.png", "desc":"砍伐树木后收集的木材。用于搭建木质体素，每块消耗 1 份。"},
	"stone": {"name":"石块", "type":"材料", "category":"material", "rarity":"common", "stack_max":999,
		"icon":"res://assets/ui/building/stone_floor.png", "desc":"使用矿镐采集石块获得。用于搭建石质体素，每块消耗 1 份。"},
	"soil": {"name":"泥土", "type":"材料", "category":"material", "rarity":"common", "stack_max":999,
		"icon":"", "icon_fallback":"土", "desc":"在旷野使用矿镐挖掘地表获得，可用于后续回填与制作。"},

	"hp_potion": {
		"name": "治疗药水",
		"type": "消耗品",
		"icon": HP_POTION_ICON,
		"category": "consumable",
		"rarity": "common",
		"stack_max": 5,
		"stats": [{"name": "恢复生命", "value": "+30"}],
		"useEffect": {"hp": 30},
		"useCooldown": 0.0,
		"desc": "一瓶红色的药水，恢复 30 生命",
	},
	"mp_potion": {
		"name": "魔力药水",
		"type": "消耗品",
		"icon": MP_POTION_ICON,
		"category": "consumable",
		"rarity": "common",
		"stack_max": 3,
		"stats": [{"name": "恢复魔法", "value": "+25"}],
		"useEffect": {"mp": 25},
		"useCooldown": 0.0,
		"desc": "一瓶蓝色的药水，恢复 25 魔法",
	},
	# ---- NPC 面板消耗品 / 材料（旧版 data 对齐，2026-08-09 迁移）----
	"enhancement_stone": {
		"name": "强化石",
		"type": "材料",
		"icon": "",
		"icon_fallback": "💎",
		"category": "material",
		"rarity": "common",
		"stack_max": 99,
		"price": 50,
		"desc": "用于强化装备的基础材料。",
	},
	"reforge_ticket": {
		"name": "改造券",
		"type": "材料",
		"icon": "",
		"icon_fallback": "🔧",
		"category": "material",
		"rarity": "uncommon",
		"stack_max": 99,
		"price": 200,
		"desc": "用于武器改造的票券（首次 1 张，替换 4 张）。",
	},
	"magic_dust": {
		"name": "魔法粉尘",
		"type": "材料",
		"icon": "",
		"icon_fallback": "✨",
		"category": "material",
		"rarity": "mythic",
		"stack_max": 999,
		"price": 10,
		"desc": "用于附魔的魔法粉尘。",
	},
	"enchant_scroll_heavy": {
		"name": "附魔卷轴：沉重",
		"type": "附魔卷轴",
		"icon": "",
		"icon_fallback": "⚔️",
		"category": "consumable",
		"scroll_id": "heavy",
		"grade": "common",
		"stack_max": 99,
		"price": 500,
		"desc": "可以给近战武器附魔前缀「沉重」。",
	},
	"enchant_scroll_sharp": {
		"name": "附魔卷轴：锋利的",
		"type": "附魔卷轴",
		"icon": "",
		"icon_fallback": "⚔️",
		"category": "consumable",
		"scroll_id": "sharp",
		"grade": "common",
		"stack_max": 99,
		"price": 500,
		"desc": "可以给剑类武器附魔前缀「锋利的」。",
	},
	"enchant_scroll_tarantula": {
		"name": "附魔卷轴：狼蛛",
		"type": "附魔卷轴",
		"icon": "",
		"icon_fallback": "🕷️",
		"category": "consumable",
		"scroll_id": "tarantula",
		"grade": "uncommon",
		"stack_max": 99,
		"price": 1000,
		"desc": "可以给任意武器附魔后缀「狼蛛」。",
	},
	"enchant_scroll_skeleton": {
		"name": "附魔卷轴：骷髅射手",
		"type": "附魔卷轴",
		"icon": "",
		"icon_fallback": "🦴",
		"category": "consumable",
		"scroll_id": "skeletonArcher",
		"grade": "rare",
		"stack_max": 99,
		"price": 2000,
		"desc": "可以给枪械类武器附魔后缀「骷髅射手」。",
	},
	# ---- 祭坛系统：祭品（按稀有度）----
	"tribute_common": {
		"name": "时空遗物·普通",
		"type": "祭品",
		"icon": "",
		"icon_fallback": "🪨",
		"category": "tribute",
		"rarity": "common",
		"stack_max": 99,
		"price": 50,
		"stats": [{"name": "防御", "value": "+1%"}],
		"desc": "来自时空裂隙的普通祭品。",
	},
	"tribute_uncommon": {
		"name": "时空遗物·优质",
		"type": "祭品",
		"icon": "",
		"icon_fallback": "🪙",
		"category": "tribute",
		"rarity": "uncommon",
		"stack_max": 99,
		"price": 150,
		"stats": [{"name": "防御", "value": "+3%"}],
		"desc": "品质稍好的时空祭品。",
	},
	"tribute_rare": {
		"name": "时空遗物·稀有",
		"type": "祭品",
		"icon": "",
		"icon_fallback": "💠",
		"category": "tribute",
		"rarity": "rare",
		"stack_max": 99,
		"price": 400,
		"stats": [{"name": "防御", "value": "+6%"}],
		"desc": "稀有的时空祭品。",
	},
	"tribute_epic": {
		"name": "时空遗物·史诗",
		"type": "祭品",
		"icon": "",
		"icon_fallback": "🏆",
		"category": "tribute",
		"rarity": "epic",
		"stack_max": 99,
		"price": 800,
		"stats": [{"name": "防御", "value": "+10%"}],
		"desc": "史诗级的时空祭品。",
	},
	"tribute_mythic": {
		"name": "时空遗物·神话",
		"type": "祭品",
		"icon": "",
		"icon_fallback": "👑",
		"category": "tribute",
		"rarity": "mythic",
		"stack_max": 99,
		"price": 1600,
		"stats": [{"name": "防御", "value": "+15%"}],
		"desc": "神话级的时空祭品。",
	},
	"tribute_legendary": {
		"name": "时空遗物·传说",
		"type": "祭品",
		"icon": "",
		"icon_fallback": "🌟",
		"category": "tribute",
		"rarity": "legendary",
		"stack_max": 99,
		"price": 3200,
		"stats": [{"name": "防御", "value": "+22%"}],
		"desc": "传说级的时空祭品。",
	},
}

var _seq := 0

func _init() -> void:
	_load_equipment()

## 加载旧版 equipment.json：iconImage/slotImage 重映射到本地装备图标目录，
## 没复制图标的保留 emoji 到 icon_fallback（UI 空纹理时回退显示）。
func _load_equipment() -> void:
	var f := FileAccess.open(EQUIPMENT_JSON, FileAccess.READ)
	if f == null:
		return
	var data = JSON.parse_string(f.get_as_text())
	f.close()
	if not (data is Dictionary) or not data.has("equipment"):
		return
	var eq: Dictionary = data["equipment"]
	for id in eq.keys():
		var def: Dictionary = eq[id].duplicate(true)
		# Original definitions own gameplay values; only adapt Godot consumption fields.
		if _defs.has(id) and _defs[id].has("scroll_id"):
			def["scroll_id"] = _defs[id].scroll_id
		def["id"] = id
		def["stack_max"] = Rules.max_stack(def)
		if not def.has("useEffect") and _defs.has(id):
			def["useEffect"] = _defs[id].get("useEffect", {}).duplicate(true)
		var emoji := String(def.get("icon", ""))
		var icon_path := String(def.get("slotImage", def.get("iconImage", "")))
		if icon_path != "":
			var mapped := "res://assets/original_ui/" + icon_path
			if not ResourceLoader.exists(mapped):
				mapped = ""
			for dir in EQUIP_ICON_DIRS:
				if not mapped.is_empty():
					break
				var candidate: String = dir + icon_path.get_file()
				if ResourceLoader.exists(candidate):
					mapped = candidate
					break
			if mapped != "":
				def["icon"] = mapped
			else:
				def["icon"] = ""
		elif emoji != "":
			def["icon"] = ""
		if emoji != "" and emoji != String(def.get("icon", "")):
			def["icon_fallback"] = emoji
		_defs[id] = def

func has_item(id: String) -> bool:
	return _defs.has(id)

func get_def(id: String) -> Dictionary:
	return _defs.get(id, {})

func get_all_ids() -> Array:
	return _defs.keys()

## 深拷贝定义并生成唯一实例 ID（对应旧版 ItemDatabase.createInstance）
func create_instance(id: String, stack := 1) -> Dictionary:
	var def: Dictionary = get_def(id)
	if def.is_empty():
		return {}
	var inst: Dictionary = def.duplicate(true)
	inst["id"] = id
	inst["stack"] = maxi(1, stack)
	inst["slot"] = -1
	_seq += 1
	inst["instance_id"] = Rules.new_id()
	return inst
