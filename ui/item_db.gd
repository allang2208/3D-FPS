extends RefCounted
## 物品库（从旧 2D 项目 data/equipment.json 的消耗品迁移）
## 字段沿用旧版：id / name / type / icon / category / rarity / stack / stack_max /
##               stats / useEffect / useCooldown / desc

const HP_POTION_ICON := "res://assets/ui/icons/health_potion.png"
const MP_POTION_ICON := "res://assets/ui/icons/mana_potion.png"

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

func has_item(id: String) -> bool:
	return _defs.has(id)

func get_def(id: String) -> Dictionary:
	return _defs.get(id, {})

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
