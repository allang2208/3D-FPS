extends RefCounted
## 加工槽只是暂存位置；拖动开始不删除，验证及容量预演成功后才提交。
const Rules = preload("res://ui/item_rules.gd")
const Spatial = preload("res://ui/spatial_inventory.gd")
const Backpack = preload("res://ui/backpack.gd")
const Equipment = preload("res://ui/equipment.gd")

static func resolve(data: Dictionary) -> Dictionary:
	if data.get("type") != "panel_item" or not data.get("owner") is WeakRef:
		return {}
	var owner: Node = data.owner.get_ref()
	var field := str(data.get("field", ""))
	if owner == null or not owner.is_open() or not owner._inventory_drag_fields.has(field):
		return {}
	var value: Dictionary = owner.get(field)
	var item: Dictionary = value.get("item", {}) if owner._inventory_drag_fields[field] else value
	if item.is_empty() or item != data.get("item", {}):
		return {}
	return {"owner": owner, "field": field, "item": item}

static func finish(source: Dictionary) -> void:
	source.owner.set(source.field, {})
	if source.field in ["_scroll", "_equip"]:
		source.owner.set(source.field + "_src", {})

static func return_enchantment(source: Dictionary) -> bool:
	# 原版附魔拖回触发 returnScroll/returnEquip，按入槽来源归还。
	if source.field not in ["_scroll", "_equip"]:
		return false
	source.owner.call("_return_scroll" if source.field == "_scroll" else "_return_equip")
	source.owner._refresh()
	return true

static func to_backpack(data: Dictionary, backpack, target: int) -> bool:
	var source := resolve(data)
	if source.is_empty() or target < 0 or target >= backpack.max_slots:
		return false
	if return_enchantment(source):
		return source.owner.get(source.field).is_empty()
	var proposed := Spatial.insert(backpack.slots, source.item, target)
	if proposed.is_empty():
		source.owner.show_message("背包已满，物品保留在加工槽", true)
		return false
	finish(source)
	backpack.slots = proposed
	backpack.changed.emit()
	source.owner._refresh()
	return true

static func to_equipment(data: Dictionary, equipment, key: String) -> bool:
	var source := resolve(data)
	if source.is_empty() or equipment == null:
		return false
	if return_enchantment(source):
		return source.owner.get(source.field).is_empty()
	if not equipment.can_equip_to(key, source.item):
		return false
	var bp = equipment._backpack
	var proposed_bp: Array = bp.slots.duplicate(true)
	var next: Dictionary = equipment.slots.duplicate(true)
	var displaced: Array[String] = [key]
	if bool(source.item.get("isTwoHanded", false)):
		displaced.append("offhand" if key == "weapon" else "ring2")
	elif Equipment.is_support(source.item):
		var main_key := "weapon" if key == "offhand" else "weapon2"
		if next[main_key] != null and bool(next[main_key].get("isTwoHanded", false)):
			displaced.append(main_key)
	for old_key in displaced:
		if next[old_key] == null:
			continue
		proposed_bp = Spatial.insert(proposed_bp, next[old_key])
		if proposed_bp.is_empty():
			source.owner.show_message("背包空间不足，无法放回替换装备", true)
			return false
		next[old_key] = null
	var equipped: Dictionary = source.item.duplicate(true)
	equipped.backpack_slot = -1
	equipped.slot = -1
	next[key] = equipped
	finish(source)
	bp.slots = proposed_bp
	equipment.slots = next
	bp.changed.emit()
	equipment.changed.emit()
	equipment.equipped.emit(key)
	source.owner._refresh()
	return true
