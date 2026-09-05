extends RefCounted
## 仓库数据模型（warehouse-system.js 迁移，精简）：按名称堆叠，5 页 x 20 格 = 100。
## 强化/改造/附魔的材料扣减走 count_material / consume_material（背包不足时仓库兜底）。

signal changed

const PAGE_SIZE := 20
const PAGE_COUNT := 5
const CAPACITY := 100

var items: Array = []
var current_page := 0

const Rules := preload("res://ui/item_rules.gd")

func _max_stack(item: Dictionary) -> int:
	return Rules.max_stack(item)

func _as_slots() -> Array:
	var result: Array = []
	result.resize(CAPACITY)
	for item in items:
		var slot := int(item.get("slot", -1))
		if slot >= 0 and slot < CAPACITY:
			result[slot] = item
	return result

func add_item(item: Dictionary, preferred := -1) -> bool:
	var proposed := Rules.insert(_as_slots(), item, CAPACITY, preferred)
	if proposed.is_empty():
		return false
	items = proposed.filter(func(it): return it != null)
	changed.emit()
	return true

func store_from_backpack(backpack, source: int, preferred := -1) -> bool:
	if source < 0 or source >= backpack.slots.size() or backpack.slots[source] == null:
		return false
	if preferred >= 0:
		var moved := Rules.transfer_at(backpack.slots, _as_slots(), source, preferred)
		if moved.is_empty():
			return false
		backpack.slots = moved.source
		items = moved.target.filter(func(it): return it != null)
		backpack.changed.emit()
		changed.emit()
		return true
	var proposed := Rules.insert(_as_slots(), backpack.slots[source], CAPACITY, preferred)
	if proposed.is_empty():
		return false
	items = proposed.filter(func(it): return it != null)
	backpack.slots[source] = null
	backpack.changed.emit()
	changed.emit()
	return true

func retrieve_to_backpack(backpack, source: int, preferred := -1) -> bool:
	var item := get_item_at(source)
	if item.is_empty():
		return false
	if preferred >= 0:
		var moved := Rules.transfer_at(_as_slots(), backpack.slots, source, preferred)
		if moved.is_empty():
			return false
		items = moved.source.filter(func(it): return it != null)
		backpack.slots = moved.target
		backpack.changed.emit()
		changed.emit()
		return true
	var proposed := Rules.insert(backpack.slots, item, backpack.max_slots, preferred)
	if proposed.is_empty():
		return false
	items.erase(item)
	backpack.slots = proposed
	backpack.changed.emit()
	changed.emit()
	return true

func serialize() -> Dictionary:
	return {"items": items.duplicate(true), "page": current_page}

func restore(data: Dictionary) -> void:
	items = data.get("items", []).duplicate(true)
	current_page = clampi(int(data.get("page", 0)), 0, PAGE_COUNT - 1)
	changed.emit()

func sort_items() -> void:
	items.sort_custom(func(a, b): return str(a.get("category", "")) + str(a.get("name", "")) < str(b.get("category", "")) + str(b.get("name", "")))
	for i in items.size():
		items[i].slot = i
	changed.emit()

func count_material(pred: Callable) -> int:
	var total := 0
	for it in items:
		if it != null and pred.call(it):
			total += int(it.get("stack", 1))
	return total

func consume_material(pred: Callable, amount: int) -> int:
	var remaining := amount
	for i in range(items.size() - 1, -1, -1):
		var it = items[i]
		if it == null or not pred.call(it):
			continue
		var stack := int(it.get("stack", 1))
		if stack <= remaining:
			remaining -= stack
			items.remove_at(i)
		else:
			it["stack"] = stack - remaining
			remaining = 0
		if remaining <= 0:
			break
	var used := amount - remaining
	if used > 0:
		changed.emit()
	return used

func get_item_at(slot: int) -> Dictionary:
	for it in items:
		if it != null and int(it.get("slot", -1)) == slot:
			return it
	return {}

func retrieve_all_to_backpack(backpack) -> void:
	for item in items.duplicate():
		if not retrieve_to_backpack(backpack, int(item.slot)):
			break

func move_item(from: int, to: int) -> bool:
	var packed := _as_slots()
	if from < 0 or from >= CAPACITY or to < 0 or to >= CAPACITY or packed[from] == null or from == to:
		return false
	if packed[to] != null and Rules.can_stack(packed[from], packed[to]):
		var amount := mini(int(packed[from].stack), Rules.max_stack(packed[to]) - int(packed[to].stack))
		packed[to].stack = int(packed[to].stack) + amount
		packed[from].stack = int(packed[from].stack) - amount
		if int(packed[from].stack) == 0:
			packed[from] = null
	else:
		var temp = packed[from]
		packed[from] = packed[to]
		packed[to] = temp
	for i in packed.size():
		if packed[i] != null:
			packed[i].slot = i
	items = packed.filter(func(it): return it != null)
	changed.emit()
	return true
