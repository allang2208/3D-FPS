extends RefCounted
## 仓库数据模型（warehouse-system.js 迁移，精简）：按名称堆叠，5 页 x 20 格 = 100。
## 强化/改造/附魔的材料扣减走 count_material / consume_material（背包不足时仓库兜底）。

signal changed

const PAGE_SIZE := 20
const PAGE_COUNT := 5
const CAPACITY := 100

var items: Array = []
var current_page := 0

func _max_stack(item: Dictionary) -> int:
	# 旧版 warehouse-system.js：无 maxStack 字段的非堆叠物品按 1（武器不叠）
	var v := int(item.get("stack_max", 0))
	return v if v > 1 else 1

func add_item(item: Dictionary) -> bool:
	var remaining := int(item.get("stack", 1))
	var max_stack := _max_stack(item)
	var name := String(item.get("name", ""))
	for it in items:
		if it != null and String(it.get("name", "")) == name and int(it.get("stack", 1)) < max_stack:
			var add := mini(max_stack - int(it["stack"]), remaining)
			it["stack"] = int(it["stack"]) + add
			remaining -= add
			if remaining <= 0:
				changed.emit()
				return true
	while remaining > 0:
		if items.size() >= CAPACITY:
			changed.emit()
			return false
		var add := mini(max_stack, remaining)
		var clone: Dictionary = item.duplicate(true)
		clone["stack"] = add
		clone["slot"] = items.size()
		items.append(clone)
		remaining -= add
	changed.emit()
	return true

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
	for i in range(items.size() - 1, -1, -1):
		var it = items[i]
		if it == null:
			continue
		if not backpack.add_item(String(it.get("id", "")), int(it.get("stack", 1))):
			break  # 背包满：保留剩余仓库物品，不丢失
		items.remove_at(i)
	changed.emit()
