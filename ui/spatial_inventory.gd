extends RefCounted
## 16x8 Diablo-style backpack placement rules.
## `slots` stores an item only at its top-left anchor. Occupied cells resolve
## through an ephemeral anchor map, so every instance is serialized once.

const COLUMNS := 16
const ROWS := 8
const CAPACITY := COLUMNS * ROWS
const Rules := preload("res://ui/item_rules.gd")

static func footprint(item: Dictionary) -> Vector2i:
	var explicit := Vector2i(maxi(1, int(item.get("grid_w", 0))), maxi(1, int(item.get("grid_h", 0))))
	if int(item.get("grid_w", 0)) > 0 and int(item.get("grid_h", 0)) > 0:
		return Vector2i(mini(COLUMNS, explicit.x), mini(ROWS, explicit.y))
	var slot := str(item.get("equipSlot", ""))
	var category := str(item.get("category", ""))
	var weapon_type := str(item.get("weaponType", ""))
	if weapon_type == "pistol": return Vector2i(3, 2)
	if weapon_type in ["shield", "spellbook", "magic_book"] or category == "magic_book": return Vector2i(2, 3)
	if item.has("rangedType") or weapon_type == "rifle" or category == "weapon_ranged": return Vector2i(8, 2)
	if category == "weapon_melee": return Vector2i(2, 4) if bool(item.get("isTwoHanded", false)) else Vector2i(1, 3)
	if item.has("weaponType") or category == "weapon": return Vector2i(8, 2) if bool(item.get("isTwoHanded", false)) else Vector2i(3, 2)
	match slot:
		"armor": return Vector2i(3, 4)
		"helmet", "gloves", "boots": return Vector2i(2, 2)
		"cloak", "backpack": return Vector2i(3, 3)
		"belt": return Vector2i(2, 1)
		_:
			return Vector2i.ONE

static func anchor_position(anchor: int) -> Vector2i:
	return Vector2i(anchor % COLUMNS, anchor / COLUMNS)

static func anchor_index(cell: Vector2i) -> int:
	return cell.y * COLUMNS + cell.x

static func normalize_at(item: Dictionary, anchor: int) -> Dictionary:
	var result := Rules.normalize(item)
	var size := footprint(result)
	var pos := anchor_position(anchor)
	result["slot"] = anchor
	result["grid_x"] = pos.x
	result["grid_y"] = pos.y
	result["grid_w"] = size.x
	result["grid_h"] = size.y
	return result

static func occupancy(slots: Array, ignored_anchor := -1) -> Array[int]:
	var result: Array[int] = []
	result.resize(CAPACITY)
	result.fill(-1)
	for anchor in mini(slots.size(), CAPACITY):
		if anchor == ignored_anchor or slots[anchor] == null:
			continue
		var item: Dictionary = slots[anchor]
		var size := footprint(item)
		var pos := anchor_position(anchor)
		for y in range(pos.y, mini(ROWS, pos.y + size.y)):
			for x in range(pos.x, mini(COLUMNS, pos.x + size.x)):
				result[anchor_index(Vector2i(x, y))] = anchor
	return result

static func owner_at(slots: Array, cell: int) -> int:
	if cell < 0 or cell >= CAPACITY:
		return -1
	return occupancy(slots)[cell]

static func can_place(slots: Array, item: Dictionary, anchor: int, ignored_anchor := -1) -> bool:
	if anchor < 0 or anchor >= CAPACITY or item.is_empty():
		return false
	var pos := anchor_position(anchor)
	var size := footprint(item)
	if pos.x + size.x > COLUMNS or pos.y + size.y > ROWS:
		return false
	var occupied := occupancy(slots, ignored_anchor)
	for y in range(pos.y, pos.y + size.y):
		for x in range(pos.x, pos.x + size.x):
			if occupied[anchor_index(Vector2i(x, y))] >= 0:
				return false
	return true

static func first_fit(slots: Array, item: Dictionary, preferred := -1, ignored_anchor := -1) -> int:
	if preferred >= 0 and can_place(slots, item, preferred, ignored_anchor):
		return preferred
	for anchor in CAPACITY:
		if can_place(slots, item, anchor, ignored_anchor):
			return anchor
	return -1

## Atomic insert: fill compatible stacks first, then place every overflow stack.
static func insert(current: Array, item: Dictionary, preferred := -1) -> Array:
	if item.is_empty() or int(item.get("stack", 1)) <= 0:
		return []
	var result := current.duplicate(true)
	result.resize(CAPACITY)
	var source := Rules.normalize(item)
	var remaining := int(source.stack)
	for anchor in result.size():
		if result[anchor] == null or not Rules.can_stack(result[anchor], source):
			continue
		var amount := mini(remaining, Rules.max_stack(source) - int(result[anchor].stack))
		result[anchor].stack = int(result[anchor].stack) + amount
		remaining -= amount
		if remaining == 0:
			return result
	var first := true
	while remaining > 0:
		var part := source.duplicate(true)
		part.stack = mini(remaining, Rules.max_stack(source))
		if not first:
			part.instance_id = Rules.new_id()
		var target := first_fit(result, part, preferred if first else -1)
		if target < 0:
			return []
		result[target] = normalize_at(part, target)
		remaining -= int(part.stack)
		first = false
	return result

static func move(current: Array, from_anchor: int, target_cell: int) -> Array:
	if from_anchor < 0 or from_anchor >= current.size() or current[from_anchor] == null:
		return []
	var target_anchor := owner_at(current, target_cell)
	if target_anchor == from_anchor:
		return current.duplicate(true)
	var result := current.duplicate(true)
	var moving: Dictionary = result[from_anchor]
	result[from_anchor] = null
	if target_anchor < 0:
		if not can_place(result, moving, target_cell):
			return []
		result[target_cell] = normalize_at(moving, target_cell)
		return result
	var displaced: Dictionary = result[target_anchor]
	result[target_anchor] = null
	if not can_place(result, moving, target_anchor) or not can_place(result, displaced, from_anchor):
		return []
	result[target_anchor] = normalize_at(moving, target_anchor)
	result[from_anchor] = normalize_at(displaced, from_anchor)
	return result

static func pack(items: Array) -> Array:
	var ordered := items.duplicate(true)
	ordered.sort_custom(func(a, b):
		var sa := footprint(a)
		var sb := footprint(b)
		var aa := sa.x * sa.y
		var ab := sb.x * sb.y
		if aa != ab: return aa > ab
		return str(a.get("category", "")) + str(a.get("name", "")) + str(a.get("instance_id", "")) < str(b.get("category", "")) + str(b.get("name", "")) + str(b.get("instance_id", "")))
	var result: Array = []
	result.resize(CAPACITY)
	for item in ordered:
		var anchor := first_fit(result, item)
		if anchor < 0:
			return []
		result[anchor] = normalize_at(item, anchor)
	return result

static func migrate_legacy(current: Array) -> Array:
	return migrate_with_overflow(current).slots

## Restore a spatial save without disturbing valid player-authored placement.
## Invalid/overlapping anchors are relocated by first-fit; only items that truly
## cannot fit are returned as overflow.
static func restore_placements(current: Array) -> Dictionary:
	var result: Array = []
	result.resize(CAPACITY)
	var overflow: Array = []
	for source_index in current.size():
		var raw = current[source_index]
		if not raw is Dictionary or raw.is_empty():
			continue
		var item: Dictionary = raw.duplicate(true)
		var preferred := int(item.get("slot", source_index))
		if preferred < 0 or preferred >= CAPACITY:
			preferred = source_index
		var anchor := preferred if can_place(result, item, preferred) else first_fit(result, item)
		if anchor < 0:
			overflow.append(item)
		else:
			result[anchor] = normalize_at(item, anchor)
	return {"slots": result, "overflow": overflow}

## Preserve the visible row/column coordinates of an older spatial save when
## the grid dimensions change, then first-fit only placements that no longer fit.
static func restore_from_grid(current: Array, source_columns: int) -> Dictionary:
	var result: Array = []
	result.resize(CAPACITY)
	var overflow: Array = []
	var old_columns := maxi(1, source_columns)
	for source_index in current.size():
		var raw = current[source_index]
		if not raw is Dictionary or raw.is_empty():
			continue
		var item: Dictionary = raw.duplicate(true)
		var old_anchor := int(item.get("slot", source_index))
		var old_position := Vector2i(int(item.get("grid_x", old_anchor % old_columns)), int(item.get("grid_y", old_anchor / old_columns)))
		var preferred := anchor_index(old_position) if old_position.x < COLUMNS and old_position.y < ROWS else -1
		var anchor := preferred if preferred >= 0 and can_place(result, item, preferred) else first_fit(result, item)
		if anchor < 0:
			overflow.append(item)
		else:
			result[anchor] = normalize_at(item, anchor)
	return {"slots": result, "overflow": overflow}

static func migrate_with_overflow(current: Array) -> Dictionary:
	var items: Array = []
	for item in current:
		if item is Dictionary and not item.is_empty():
			var clean: Dictionary = item.duplicate(true)
			for key in ["grid_x", "grid_y", "grid_w", "grid_h"]:
				clean.erase(key)
			items.append(clean)
	items.sort_custom(func(a, b):
		var sa := footprint(a)
		var sb := footprint(b)
		return sa.x * sa.y > sb.x * sb.y)
	var result: Array = []
	result.resize(CAPACITY)
	var overflow: Array = []
	for item in items:
		var anchor := first_fit(result, item)
		if anchor < 0:
			overflow.append(item.duplicate(true))
		else:
			result[anchor] = normalize_at(item, anchor)
	return {"slots": result, "overflow": overflow}

static func used_cells(slots: Array) -> int:
	var count := 0
	for owner in occupancy(slots):
		if owner >= 0:
			count += 1
	return count
