extends RefCounted
## 背包数据模型（从旧 2D 项目 EquipManager/backpack 迁移，独立于 UI）
##
## - slots: 36 格（旧版 inventory-grid 6 列）；每格一个 Dictionary 或 null
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
var max_slots := 25

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

## 加入物品：先堆叠同类（不超过 stack_max），再占空位；满则失败
func add_item(id: String, count := 1) -> bool:
	var remaining := count
	for i in slots.size():
		if slots[i] == null:
			continue
		var it: Dictionary = slots[i]
		if String(it.get("id", "")) == id:
			var stack_max: int = it.get("stack_max", 99)
			var room: int = stack_max - int(it.get("stack", 1))
			if room > 0:
				var take := mini(room, remaining)
				it["stack"] = int(it.get("stack", 1)) + take
				remaining -= take
				if remaining <= 0:
					changed.emit()
					item_added.emit(i)
					return true
	for i in slots.size():
		if slots[i] == null:
			var inst: Dictionary = _db.create_instance(id, remaining)
			if inst.is_empty():
				return false
			inst["slot"] = i
			slots[i] = inst
			changed.emit()
			item_added.emit(i)
			return true
	return false

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
	var i := find_slot(instance_id)
	if i < 0:
		return false
	var it: Dictionary = slots[i]
	var stack: int = it.get("stack", 1)
	if count >= stack:
		slots[i] = null
	else:
		it["stack"] = stack - count
	changed.emit()
	return true

func swap_items(a: int, b: int) -> void:
	if a < 0 or a >= slots.size() or b < 0 or b >= slots.size() or a == b:
		return
	var tmp = slots[a]
	slots[a] = slots[b]
	slots[b] = tmp
	if slots[a] != null:
		slots[a]["slot"] = a
	if slots[b] != null:
		slots[b]["slot"] = b
	changed.emit()

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
func use_item(instance_id: String, player: Object) -> Dictionary:
	var i := find_slot(instance_id)
	if i < 0:
		return {"ok": false, "message": "物品不存在"}
	if get_cooldown(instance_id) > 0.0:
		return {"ok": false, "message": "冷却中", "cooldown": true}
	var it: Dictionary = slots[i]
	var effect: Dictionary = it.get("useEffect", {})
	var applied := false
	if int(effect.get("hp", 0)) > 0:
		if player != null and player.has_method("heal"):
			player.heal(int(effect.get("hp", 0)))
			applied = true
	if int(effect.get("mp", 0)) > 0:
		if player != null and player.has_method("add_mp"):
			player.add_mp(int(effect.get("mp", 0)))
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

func use_hotbar(index: int, player: Object) -> Dictionary:
	var item := resolve_hotbar(index)
	if item.is_empty():
		return {"ok": false, "message": "快捷栏为空"}
	return use_item(String(item.get("instance_id", "")), player)
