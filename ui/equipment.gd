extends RefCounted
## 装备栏数据模型（从旧版 EquipManager.equipFromBackpack / unequip 迁移）
## - 15 槽位沿用旧版装备页：earring/helmet/ring1/gloves/necklace/cloak/weapon/armor/
##   offhand/weapon2/belt/ring2/extra/boots/backpack
## - 武器槽规则（旧版）：盾→offhand/ring2；双手武器→主手并卸下副手；
##   单手武器→优先主手空位再副手；装备副手时若主手是双手武器则先卸下主手
## - 被替换装备回背包（优先回来源格）

signal changed
signal equipped(slot: String)

const SLOT_ORDER := [
	"earring", "helmet", "ring1", "gloves", "necklace", "cloak",
	"weapon", "armor", "offhand", "weapon2", "belt", "ring2",
	"extra", "boots", "backpack",
]

var slots := {}  # key -> Dictionary|null

var _backpack: RefCounted

func _init(backpack: RefCounted) -> void:
	_backpack = backpack
	for k in SLOT_ORDER:
		slots[k] = null

func get_item(key: String) -> Dictionary:
	var v = slots.get(key, null)
	return v if v != null else {}

func equipped_count() -> int:
	var n := 0
	for k in SLOT_ORDER:
		if slots[k] != null:
			n += 1
	return n

## 双手武器锁定：offhand 被 weapon 锁、ring2 被 weapon2 锁（旧版渲染逻辑）
func is_locked(key: String) -> bool:
	if key == "offhand":
		return slots.get("weapon", {}) != null and bool(slots["weapon"].get("isTwoHanded", false))
	if key == "ring2":
		return slots.get("weapon2", {}) != null and bool(slots["weapon2"].get("isTwoHanded", false))
	return false

## 背包装备（对应旧版 equipFromBackpack）
func equip_from_backpack(backpack_slot: int) -> bool:
	if _backpack == null or backpack_slot < 0 or backpack_slot >= _backpack.slots.size():
		return false
	var item: Dictionary = _backpack.slots[backpack_slot]
	if item.is_empty():
		return false
	var target := _resolve_target_slot(item)
	if target == "":
		return false
	return equip_to_slot(target, backpack_slot)

## 显式装备到指定槽位（拖放用；兼容性由 can_equip_to 保证）
func equip_to_slot(key: String, backpack_slot: int) -> bool:
	if not slots.has(key) or _backpack == null:
		return false
	if backpack_slot < 0 or backpack_slot >= _backpack.slots.size():
		return false
	var item: Dictionary = _backpack.slots[backpack_slot]
	if item.is_empty() or not can_equip_to(key, item):
		return false
	_apply_two_handed_rules(item, key)
	var replaced: Dictionary = get_item(key)
	_backpack.slots[backpack_slot] = replaced.duplicate(true) if not replaced.is_empty() else null
	if not replaced.is_empty():
		_backpack.slots[backpack_slot]["slot"] = backpack_slot
	var clone: Dictionary = item.duplicate(true)
	clone["backpack_slot"] = backpack_slot
	clone["slot"] = -1
	slots[key] = clone
	_backpack.changed.emit()
	changed.emit()
	equipped.emit(key)
	return true

## 卸下装备回背包（优先来源格，其次首个空位）
func unequip(key: String) -> bool:
	var item: Dictionary = slots.get(key, {})
	if item.is_empty() or _backpack == null:
		return false
	var put_slot := -1
	var remembered := int(item.get("backpack_slot", -1))
	if remembered >= 0 and remembered < _backpack.slots.size() and _backpack.slots[remembered] == null:
		put_slot = remembered
	else:
		for i in _backpack.slots.size():
			if _backpack.slots[i] == null:
				put_slot = i
				break
	if put_slot < 0:
		return false
	var clone: Dictionary = item.duplicate(true)
	clone["slot"] = put_slot
	_backpack.slots[put_slot] = clone
	slots[key] = null
	_backpack.changed.emit()
	changed.emit()
	return true

func swap_equip(a: String, b: String) -> bool:
	if not slots.has(a) or not slots.has(b) or a == b:
		return false
	if is_locked(a) or is_locked(b):
		return false
	var tmp = slots[a]
	slots[a] = slots[b]
	slots[b] = tmp
	changed.emit()
	return true

## 目标槽位判定（旧版武器栏填充逻辑简化版）
func _resolve_target_slot(item: Dictionary) -> String:
	var category := String(item.get("category", ""))
	if category.begins_with("weapon"):
		var weapon_type := String(item.get("weaponType", ""))
		if weapon_type == "shield":
			if slots["offhand"] == null or not is_locked("offhand"):
				return "offhand"
			if slots["ring2"] == null or not is_locked("ring2"):
				return "ring2"
			return "offhand"
		if bool(item.get("isTwoHanded", false)):
			if slots["weapon"] == null:
				return "weapon"
			if slots["weapon2"] == null:
				return "weapon2"
			return "weapon"
		if slots["weapon"] == null:
			return "weapon"
		if slots["offhand"] == null and not is_locked("offhand"):
			return "offhand"
		if slots["weapon2"] == null:
			return "weapon2"
		return "weapon"
	var equip_slot := String(item.get("equipSlot", ""))
	if equip_slot != "" and slots.has(equip_slot):
		return equip_slot
	return ""

## 双手武器/盾牌与副手互斥（旧版第 1/1b/2/2b 步）
func _apply_two_handed_rules(item: Dictionary, target: String) -> void:
	if bool(item.get("isTwoHanded", false)):
		if target == "weapon" and slots["offhand"] != null:
			_unequip_to_backpack("offhand")
		elif target == "weapon2" and slots["ring2"] != null:
			_unequip_to_backpack("ring2")
	elif String(item.get("weaponType", "")) == "shield":
		if target == "offhand" and slots["weapon"] != null and bool(slots["weapon"].get("isTwoHanded", false)):
			_unequip_to_backpack("weapon")
		elif target == "ring2" and slots["weapon2"] != null and bool(slots["weapon2"].get("isTwoHanded", false)):
			_unequip_to_backpack("weapon2")

func _unequip_to_backpack(key: String) -> void:
	var it: Dictionary = slots[key]
	if it.is_empty() or _backpack == null:
		return
	var put_slot := -1
	for i in _backpack.slots.size():
		if _backpack.slots[i] == null:
			put_slot = i
			break
	if put_slot < 0:
		return
	var clone: Dictionary = it.duplicate(true)
	clone["slot"] = put_slot
	_backpack.slots[put_slot] = clone
	slots[key] = null

## 拖放兼容性判定（装备槽接受什么物品）
func can_equip_to(key: String, item: Dictionary) -> bool:
	if item.is_empty() or is_locked(key):
		return false
	var category := String(item.get("category", ""))
	if category.begins_with("weapon"):
		if String(item.get("weaponType", "")) == "shield":
			return key == "offhand" or key == "ring2"
		if bool(item.get("isTwoHanded", false)):
			return key == "weapon" or key == "weapon2"
		return key == "weapon" or key == "weapon2" or key == "offhand" or key == "ring2"
	return String(item.get("equipSlot", "")) == key
