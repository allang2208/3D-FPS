extends RefCounted
const Rules := preload("res://ui/item_rules.gd")
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
	var value = _backpack.slots[backpack_slot]
	if value == null:
		return false
	var item: Dictionary = value
	if item.is_empty():
		return false
	var target := _resolve_target_slot(item)
	if target == "":
		return false
	return equip_to_slot(target, backpack_slot)

## 显式装备到指定槽位（拖放用；兼容性由 can_equip_to 保证）
func equip_to_slot(key: String, backpack_slot: int) -> bool:
	if _backpack == null or backpack_slot < 0 or backpack_slot >= _backpack.slots.size():
		return false
	var value = _backpack.slots[backpack_slot]
	if value == null or not can_equip_to(key, value):
		return false
	var item: Dictionary = value
	var proposed: Array = _backpack.slots.duplicate(true)
	proposed[backpack_slot] = null
	var next := slots.duplicate(true)
	var displaced: Array[String] = [key]
	if bool(item.get("isTwoHanded", false)):
		displaced.append("offhand" if key == "weapon" else "ring2")
	elif is_support(item):
		var main_key := "weapon" if key == "offhand" else "weapon2"
		if next[main_key] != null and bool(next[main_key].get("isTwoHanded", false)):
			displaced.append(main_key)
	for old_key in displaced:
		if next[old_key] != null:
			proposed = Rules.insert(proposed, next[old_key], _backpack.max_slots, backpack_slot)
			if proposed.is_empty():
				return false
		next[old_key] = null
	var clone := item.duplicate(true)
	clone["backpack_slot"] = backpack_slot
	clone["slot"] = -1
	next[key] = clone
	slots = next
	_backpack.slots = proposed
	_backpack.changed.emit()
	changed.emit()
	equipped.emit(key)
	return true

## 卸下装备回背包（优先来源格，其次首个空位）
func unequip(key: String, preferred := -1) -> bool:
	var item := get_item(key)
	if item.is_empty() or _backpack == null:
		return false
	if preferred >= 0 and preferred < _backpack.slots.size() and _backpack.slots[preferred] != null:
		return equip_to_slot(key, preferred)
	if preferred < 0:
		preferred = int(item.get("backpack_slot", -1))
	var proposed := Rules.insert(_backpack.slots, item, _backpack.max_slots, preferred)
	if proposed.is_empty():
		return false
	slots[key] = null
	_backpack.slots = proposed
	_backpack.changed.emit()
	changed.emit()
	return true

func swap_equip(a: String, b: String) -> bool:
	if not slots.has(a) or not slots.has(b) or a == b:
		return false
	if (slots[a] != null and not can_equip_to(b, slots[a])) or (slots[b] != null and not can_equip_to(a, slots[b])):
		return false
	var next := slots.duplicate(true)
	var temp = next[a]
	next[a] = next[b]
	next[b] = temp
	for pair in [["weapon", "offhand"], ["weapon2", "ring2"]]:
		if next[pair[0]] != null and bool(next[pair[0]].get("isTwoHanded", false)) and next[pair[1]] != null:
			return false
	slots = next
	changed.emit()
	return true

## 目标槽位判定（旧版武器栏填充逻辑简化版）
func _resolve_target_slot(item: Dictionary) -> String:
	var candidates: Array = []
	if is_support(item):
		candidates = ["offhand", "ring2"]
	elif is_weapon(item):
		candidates = ["weapon", "weapon2"]
	else:
		var target := str(item.get("equipSlot", ""))
		return target if slots.has(target) else ""
	for key in candidates:
		if slots[key] == null and not is_locked(key):
			return key
	return candidates[0]

static func is_support(item: Dictionary) -> bool:
	return item.get("offhandType", "") in ["shield", "spellbook", "magic_book"] or item.get("weaponType", "") in ["shield", "spellbook", "magic_book"] or item.get("category", "") == "magic_book"

static func is_weapon(item: Dictionary) -> bool:
	return item.has("weaponType") or str(item.get("category", "")).contains("weapon") or item.has("rangedType")

func can_equip_to(key: String, item: Dictionary) -> bool:
	if item.is_empty() or not slots.has(key):
		return false
	if key in ["weapon", "weapon2"]:
		return is_weapon(item) and not is_support(item)
	if key in ["offhand", "ring2"]:
		return is_support(item) and not bool(item.get("isTwoHanded", false))
	return not is_weapon(item) and str(item.get("equipSlot", "")) == key

func serialize() -> Dictionary:
	return slots.duplicate(true)

func restore(data: Dictionary) -> void:
	for key in SLOT_ORDER:
		slots[key] = data.get(key, null)
	changed.emit()
