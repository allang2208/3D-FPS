extends RefCounted
## Shared inventory rules. Definitions are immutable; transfers preserve instance data.

static func new_id() -> String:
	return Crypto.new().generate_random_bytes(16).hex_encode()

static func is_gold(item: Dictionary) -> bool:
	return item.get("category", "") == "gold" or item.get("name", "") == "金币"

static func max_stack(item: Dictionary) -> int:
	if is_gold(item):
		return 9007199254740991
	if item.get("id", "") in ["enhancement_stone", "reforge_ticket"]:
		return 9999
	return maxi(1, int(item.get("maxStack", item.get("stack_max", 1))))

static func normalize(item: Dictionary) -> Dictionary:
	var result := item.duplicate(true)
	if str(result.get("instance_id", "")).is_empty():
		result["instance_id"] = str(result.get("itemId", new_id()))
	result["stack"] = maxi(1, int(result.get("stack", 1)))
	result["stack_max"] = max_stack(result)
	return result

static func can_stack(a: Dictionary, b: Dictionary) -> bool:
	if is_gold(a) and is_gold(b):
		return true
	if max_stack(a) <= 1 or max_stack(a) != max_stack(b):
		return false
	var left := a.duplicate(true)
	var right := b.duplicate(true)
	# Spatial coordinates describe placement, not item identity. They must not
	# prevent otherwise identical stacks from merging after either item moved.
	for key in ["instance_id", "itemId", "slot", "backpack_slot", "stack", "_price", "grid_x", "grid_y", "grid_w", "grid_h"]:
		left.erase(key)
		right.erase(key)
	return left == right

## Returns a proposed array or [] on failure. The caller commits only after success.
static func insert(current: Array, item: Dictionary, capacity: int, preferred := -1) -> Array:
	if item.is_empty() or int(item.get("stack", 1)) <= 0:
		return []
	var result := current.duplicate(true)
	result.resize(capacity)
	var source := normalize(item)
	var remaining := int(source.stack)
	var order: Array[int] = []
	if preferred >= 0 and preferred < capacity:
		order.append(preferred)
	for i in capacity:
		if i != preferred:
			order.append(i)
	for i in order:
		if result[i] != null and can_stack(result[i], source):
			var amount := mini(remaining, max_stack(source) - int(result[i].stack))
			result[i].stack = int(result[i].stack) + amount
			remaining -= amount
			if remaining == 0:
				return result
	var first := true
	for i in order:
		if result[i] != null:
			continue
		var part := source.duplicate(true)
		part.stack = mini(remaining, max_stack(source))
		part.slot = i
		if not first:
			part.instance_id = new_id()
		first = false
		result[i] = part
		remaining -= int(part.stack)
		if remaining == 0:
			return result
	return []

static func transfer_at(source: Array, target: Array, from: int, to: int) -> Dictionary:
	if from < 0 or from >= source.size() or to < 0 or to >= target.size() or source[from] == null:
		return {}
	var left := source.duplicate(true)
	var right := target.duplicate(true)
	if right[to] != null and can_stack(left[from], right[to]):
		var amount := mini(int(left[from].stack), max_stack(right[to]) - int(right[to].stack))
		if amount <= 0:
			return {}
		right[to].stack = int(right[to].stack) + amount
		left[from].stack = int(left[from].stack) - amount
		if int(left[from].stack) == 0:
			left[from] = null
	else:
		var old = right[to]
		right[to] = left[from]
		left[from] = old
		if left[from] != null:
			left[from].slot = from
		right[to].slot = to
	return {"source": left, "target": right}
