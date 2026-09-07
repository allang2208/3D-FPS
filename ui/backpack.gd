extends RefCounted
const Rules := preload("res://ui/item_rules.gd")
const Spatial := preload("res://ui/spatial_inventory.gd")
## 背包数据模型（从旧 2D 项目 EquipManager/backpack 迁移，独立于 UI）
##
## - slots: 16x8 空间网格；物品只存于左上锚点，其余占用格由 Spatial 解析
## - hotbar: 1~4 快捷栏（旧版 itemGroup），绑定按 instance_id（旧版逻辑），
##   实例用完后按名称回退（旧版 _findAssignedData 行为）
## - 拖拽交换 / 绑定 / 使用均走这里，UI 只负责展示与输入

signal changed
signal item_used(item: Dictionary)
signal item_added(slot: int)
signal bound(index: int)

const HOTBAR_SIZE := 4

var slots: Array = []          # Array[Dictionary|null]，下标即背包格
var hotbar: Array = []         # Array[Dictionary|null]，{instance_id, item_name}
var max_slots := Spatial.CAPACITY
var grid_columns := Spatial.COLUMNS
var grid_rows := Spatial.ROWS
var migration_overflow: Array = []

var _db: RefCounted
var _cooldowns := {}  # instance_id -> 剩余冷却秒数

func _init(db: RefCounted) -> void:
	_db = db
	slots.resize(max_slots)
	hotbar.resize(HOTBAR_SIZE)

func item_count() -> int:
	var n := 0
	for it in slots:
		if it != null:
			n += 1
	return n

func count_item(id: String) -> int:
	var total := 0
	for item in slots:
		if item != null and str(item.get("id", "")) == id:
			total += int(item.get("stack", 1))
	return total

func take_items(id: String, requested: int) -> int:
	requested = maxi(0, requested)
	if requested == 0 or count_item(id) < requested:
		return 0
	var taken := 0
	for i in slots.size():
		var item = slots[i]
		if item == null or str(item.get("id", "")) != id:
			continue
		var amount := mini(requested - taken, int(item.get("stack", 1)))
		taken += amount
		item.stack = int(item.stack) - amount
		if int(item.stack) == 0:
			slots[i] = null
		if taken == requested:
			break
	changed.emit()
	return taken

## 加入物品：先堆叠同类（不超过 stack_max），再占空位；满则失败
func add_item(id: String, count := 1) -> bool:
	if count <= 0:
		return false
	return add_instance(_db.create_instance(id, count))

func add_instance(item: Dictionary, preferred := -1) -> bool:
	var proposed := Spatial.insert(slots, item, preferred)
	if proposed.is_empty():
		return false
	var previous := slots
	slots = proposed
	changed.emit()
	var found := find_slot(str(item.get("instance_id", "")))
	if found < 0:
		for i in slots.size():
			if slots[i] != null and Rules.can_stack(slots[i], item) \
				and (previous[i] == null or int(slots[i].get("stack", 1)) > int(previous[i].get("stack", 1))):
				found = i
				break
	if found >= 0:
		item_added.emit(found)
	return true

func can_add(item: Dictionary) -> bool:
	return not Spatial.insert(slots, item).is_empty()

func propose_insert(item: Dictionary, preferred := -1) -> Array:
	return Spatial.insert(slots, item, preferred)

func split_stack(slot: int, count: int) -> bool:
	if slot < 0 or slot >= slots.size() or slots[slot] == null:
		return false
	var item: Dictionary = slots[slot]
	if Rules.is_gold(item) or count <= 0 or count >= int(item.stack):
		return false
	var target := Spatial.first_fit(slots, item)
	if target < 0:
		return false
	var part := item.duplicate(true)
	part.instance_id = Rules.new_id()
	part.stack = count
	part = Spatial.normalize_at(part, target)
	item.stack = int(item.stack) - count
	slots[target] = part
	changed.emit()
	return true

func sort_items() -> void:
	var items: Array = slots.filter(func(it): return it != null)
	var packed := Spatial.pack(items)
	if packed.is_empty() and not items.is_empty():
		return
	slots = packed
	changed.emit()

func serialize() -> Dictionary:
	return {"grid_version": 3, "grid_columns": grid_columns, "grid_rows": grid_rows, "max_slots": max_slots, "slots": slots.duplicate(true), "hotbar": hotbar.duplicate(true), "cooldowns": _cooldowns.duplicate(true), "migration_overflow": migration_overflow.duplicate(true)}

func restore(data: Dictionary) -> void:
	max_slots = Spatial.CAPACITY
	grid_columns = Spatial.COLUMNS
	grid_rows = Spatial.ROWS
	var saved_slots: Array = data.get("slots", []).duplicate(true)
	if int(data.get("grid_version", 1)) >= 2:
		var saved_columns := int(data.get("grid_columns", 8))
		var restored := Spatial.restore_placements(saved_slots) if saved_columns == Spatial.COLUMNS else Spatial.restore_from_grid(saved_slots, saved_columns)
		slots = restored.slots
		migration_overflow = data.get("migration_overflow", []).duplicate(true)
		migration_overflow.append_array(restored.overflow)
	else:
		var migrated := Spatial.migrate_with_overflow(saved_slots)
		slots = migrated.slots
		migration_overflow = migrated.overflow
	hotbar = data.get("hotbar", []).duplicate(true)
	hotbar.resize(HOTBAR_SIZE)
	_cooldowns = data.get("cooldowns", {}).duplicate(true)
	changed.emit()

func tick_cooldowns(delta: float) -> void:
	if delta <= 0.0 or _cooldowns.is_empty():
		return
	for k in _cooldowns.keys():
		var v: float = maxf(0.0, float(_cooldowns[k]) - delta)
		if v <= 0.0:
			_cooldowns.erase(k)
		else:
			_cooldowns[k] = v

func get_cooldown(instance_id: String) -> float:
	return float(_cooldowns.get(instance_id, 0.0))

func get_cooldown_total(instance_id: String) -> float:
	var i := find_slot(instance_id)
	if i < 0:
		return 0.0
	return float(slots[i].get("useCooldown", 0.0))

func find_slot(instance_id: String) -> int:
	for i in slots.size():
		if slots[i] != null and String(slots[i].get("instance_id", "")) == instance_id:
			return i
	return -1

func remove_item(instance_id: String, count := 1) -> bool:
	if count <= 0:
		return false
	var i := find_slot(instance_id)
	if i < 0:
		return false
	var it: Dictionary = slots[i]
	var stack: int = it.get("stack", 1)
	if count > stack:
		return false
	if count >= stack:
		slots[i] = null
	else:
		it["stack"] = stack - count
	changed.emit()
	return true

func swap_items(a: int, b: int) -> void:
	var proposed := Spatial.move(slots, a, b)
	if proposed.is_empty():
		return
	slots = proposed
	changed.emit()

func owner_at_cell(cell: int) -> int:
	return Spatial.owner_at(slots, cell)

func get_item_at_cell(cell: int) -> Dictionary:
	var anchor := owner_at_cell(cell)
	return slots[anchor] if anchor >= 0 else {}

func used_cell_count() -> int:
	return Spatial.used_cells(slots)

## 快捷栏绑定（旧版只允许消耗品进快捷栏）
func bind_hotbar(index: int, instance_id: String) -> bool:
	if index < 0 or index >= HOTBAR_SIZE:
		return false
	var i := find_slot(instance_id)
	if i < 0:
		return false
	var it: Dictionary = slots[i]
	if String(it.get("category", "")) != "consumable":
		return false
	hotbar[index] = {"instance_id": instance_id, "item_name": String(it.get("name", ""))}
	changed.emit()
	bound.emit(index)
	return true

func unbind_hotbar(index: int) -> void:
	if index >= 0 and index < HOTBAR_SIZE and hotbar[index] != null:
		hotbar[index] = null
		changed.emit()

func swap_hotbar(a: int, b: int) -> void:
	if a < 0 or a >= HOTBAR_SIZE or b < 0 or b >= HOTBAR_SIZE or a == b:
		return
	var tmp = hotbar[a]
	hotbar[a] = hotbar[b]
	hotbar[b] = tmp
	changed.emit()

## 按实例 ID 解析；实例消失后按名称回退（旧版兼容逻辑）
func resolve_hotbar(index: int) -> Dictionary:
	if index < 0 or index >= HOTBAR_SIZE:
		return {}
	if hotbar[index] == null:
		return {}
	var b: Dictionary = hotbar[index]
	var instance_id := String(b.get("instance_id", ""))
	var i := find_slot(instance_id)
	if i >= 0:
		return slots[i]
	var name := String(b.get("item_name", ""))
	if name == "":
		return {}
	for it in slots:
		if it != null and String(it.get("name", "")) == name:
			return it
	return {}

## 使用指定背包格物品；效果仅作用于存在对应接口的玩家（heal / add_mp）
func use_item(instance_id: String, player: Object, status: Object = null) -> Dictionary:
	var i := find_slot(instance_id)
	if i < 0:
		return {"ok": false, "message": "物品不存在"}
	if get_cooldown(instance_id) > 0.0:
		return {"ok": false, "message": "冷却中", "cooldown": true}
	var it: Dictionary = slots[i]
	var effect: Dictionary = it.get("useEffect", {})
	var applied := false
	var max_hp := int(player.get("max_hp")) if player != null else 0
	var max_mp := int(status.max_mp()) if status != null else 0
	var hp_amount := maxi(0, int(effect.get("hp", 0))) + int(max_hp * maxf(0, effect.get("maxHpPercent", 0)) / 100.0)
	var mp_amount := maxi(0, int(effect.get("mp", 0))) + int(max_mp * maxf(0, effect.get("maxMpPercent", 0)) / 100.0)
	if hp_amount > 0:
		if player != null and player.has_method("heal"):
			player.heal(hp_amount)
			applied = true
	if mp_amount > 0:
		if status != null:
			status.set_mp(mini(max_mp, int(status.mp) + mp_amount))
			applied = true
		elif player != null and player.has_method("add_mp"):
			player.add_mp(mp_amount)
			applied = true
	if not applied:
		return {"ok": false, "message": "%s 当前无法使用" % String(it.get("name", "物品"))}
	var stack: int = it.get("stack", 1)
	if stack <= 1:
		slots[i] = null
	else:
		it["stack"] = stack - 1
	var cd: float = float(it.get("useCooldown", 0.0))
	if cd > 0.0:
		_cooldowns[instance_id] = cd
	var used := it
	changed.emit()
	item_used.emit(used)
	return {"ok": true, "message": "已使用 %s" % String(it.get("name", "物品"))}

func use_hotbar(index: int, player: Object, status: Object = null) -> Dictionary:
	var item := resolve_hotbar(index)
	if item.is_empty():
		return {"ok": false, "message": "快捷栏为空"}
	return use_item(String(item.get("instance_id", "")), player, status)
