extends RefCounted
## 物品库：消耗品定义 + 加载旧版 data/equipment.json（125 件装备）
## 字段沿用旧版：id / name / type / icon / category / rarity / stack / stack_max /
##               stats / useEffect / useCooldown / desc / equipSlot / attack / ammoConfig ...

const HP_POTION_ICON := "res://assets/ui/icons/health_potion.png"
const MP_POTION_ICON := "res://assets/ui/icons/mana_potion.png"
const EQUIPMENT_JSON := "res://assets/data/equipment.json"
const EQUIP_ICON_DIR := "res://assets/ui/icons/equip/"

var _defs := {
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
		if _defs.has(id):
			continue  # 保留本地精修定义（药水带 stack_max/图标路径）
		var def: Dictionary = eq[id].duplicate(true)
		var emoji := String(def.get("icon", ""))
		var icon_path := String(def.get("slotImage", def.get("iconImage", "")))
		if icon_path != "":
			var mapped := EQUIP_ICON_DIR + icon_path.get_file()
			if ResourceLoader.exists(mapped):
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
	inst["stack"] = clampi(stack, 1, int(def.get("stack_max", 99)))
	inst["slot"] = -1
	_seq += 1
	inst["instance_id"] = "%d_%d" % [Time.get_ticks_usec(), _seq]
	return inst
