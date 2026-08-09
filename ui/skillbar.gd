extends RefCounted
## 快捷栏技能绑定数据层（复刻旧版 QuickBar 技能侧 + magic-categories 门槛）
## 技能效果本体未移植：绑定唯一性/换位、冷却、法杖门槛、长按标记、特殊攻击槽已就绪，
## UI 可直接消费；技能系统接入后把 skills 字典填上即可。

signal changed

const SLOT_SIZE := 4  # Q/E/X/C

var assignments := {}  # slot(int) -> skill_id(String)
var cooldowns := {}    # skill_id -> 剩余毫秒
var special := {}      # {enabled, skill_id, cooldown_ms}
var skills := {}       # skill_id -> {name, icon, cooldown_s, hold, tier}
var staff_equipped := false
var active_skill := ""  # 二段式技能正在凝聚的 skill_id（火球绕身阶段）

func setup(skills_data: Dictionary) -> void:
	skills = skills_data
	changed.emit()

func find_slot(skill_id: String) -> int:
	for s in SLOT_SIZE:
		if String(assignments.get(s, "")) == skill_id:
			return s
	return -1

func resolve(slot: int) -> String:
	if slot < 0 or slot >= SLOT_SIZE:
		return ""
	return String(assignments.get(slot, ""))

## 绑定（旧版：技能唯一，已绑其他槽则换位/清原槽；目标槽原有内容挪到源槽）
func assign(slot: int, skill_id: String) -> bool:
	if slot < 0 or slot >= SLOT_SIZE or not skills.has(skill_id):
		return false
	var src_slot := find_slot(skill_id)
	if src_slot >= 0 and src_slot != slot:
		var cur := String(assignments.get(slot, ""))
		if cur != "":
			assignments[src_slot] = cur
		else:
			assignments.erase(src_slot)
	assignments[slot] = skill_id
	changed.emit()
	return true

func unassign(slot: int) -> void:
	if slot >= 0 and slot < SLOT_SIZE and assignments.has(slot):
		assignments.erase(slot)
		changed.emit()

func swap(a: int, b: int) -> void:
	if a < 0 or a >= SLOT_SIZE or b < 0 or b >= SLOT_SIZE or a == b:
		return
	var tmp = assignments.get(a, "")
	if assignments.has(b):
		assignments[a] = assignments[b]
	else:
		assignments.erase(a)
	assignments[b] = tmp
	changed.emit()

func tick(delta_ms: float) -> void:
	if delta_ms <= 0.0 or cooldowns.is_empty():
		return
	var ended := false
	for k in cooldowns.keys():
		var v: float = maxf(0.0, float(cooldowns[k]) - delta_ms)
		if v <= 0.0:
			cooldowns.erase(k)
			ended = true
		else:
			cooldowns[k] = v
	if ended:
		changed.emit()

func get_cooldown(skill_id: String) -> float:
	return float(cooldowns.get(skill_id, 0.0))

func get_cooldown_total(skill_id: String) -> float:
	var def: Dictionary = skills.get(skill_id, {})
	return float(def.get("cooldown_s", 0.0)) * 1000.0

func set_cooldown(skill_id: String, ms: float) -> void:
	cooldowns[skill_id] = maxf(0.0, ms)
	changed.emit()

func is_hold(skill_id: String) -> bool:
	return bool(skills.get(skill_id, {}).get("hold", false))

## 使用判定（旧版 useSlot 前置检查：冷却 / 魔法法杖门槛）
func ready_check(slot: int) -> Dictionary:
	var skill_id := resolve(slot)
	if skill_id == "":
		return {"ok": false, "reason": "空槽"}
	var cd := get_cooldown(skill_id)
	if cd > 0.0:
		return {"ok": false, "reason": "冷却中 %.1f秒" % (cd / 1000.0)}
	var tier: int = int(skills.get(skill_id, {}).get("tier", 1))
	if tier >= 2 and not staff_equipped:
		return {"ok": false, "reason": "中级魔法需要装备法杖才能释放"}
	return {"ok": true, "reason": ""}

## 触发（二段式）：凝聚中再按 → 第二段发射（不扣 MP/不设冷却）；
## 第一段 → 扣 MP、不设冷却（消耗后由 consume_active 设），返回 ok + skill_id + phase
func trigger(slot: int, mp_provider: Object = null) -> Dictionary:
	var r := ready_check(slot)
	if not bool(r.get("ok", false)):
		return r
	var skill_id := resolve(slot)
	var def: Dictionary = skills.get(skill_id, {})
	var two_stage := bool(def.get("two_stage", false))
	if two_stage and active_skill == skill_id:
		return {"ok": true, "reason": "", "skill_id": skill_id, "phase": "launch"}
	var mp_cost: int = int(def.get("mp_cost", 0))
	if mp_cost > 0 and mp_provider != null:
		if int(mp_provider.get("mp")) < mp_cost:
			return {"ok": false, "reason": "魔法不足"}
		mp_provider.set_mp(int(mp_provider.get("mp")) - mp_cost)
	if two_stage:
		active_skill = skill_id
		return {"ok": true, "reason": "", "skill_id": skill_id, "phase": "spawn"}
	var cd_s: float = def.get("cooldown_s", 0.0)
	if cd_s > 0.0:
		set_cooldown(skill_id, cd_s * 1000.0)
	return {"ok": true, "reason": "", "skill_id": skill_id, "phase": "cast"}

## 二段式技能消耗完成（爆炸/超时）→ 开始冷却并清凝聚态
func consume_active(skill_id: String) -> void:
	if active_skill != skill_id:
		return
	active_skill = ""
	var cd_s: float = float(skills.get(skill_id, {}).get("cooldown_s", 0.0))
	if cd_s > 0.0:
		set_cooldown(skill_id, cd_s * 1000.0)

## 特殊攻击槽（旧版 refreshSpecialAttack：夜与火之剑/符文长剑，15s 冷却）
func refresh_special(weapon: Dictionary) -> void:
	var stype := String(weapon.get("specialAttackType", ""))
	var enabled := stype == "nightFlame" or stype == "runeSword"
	special["enabled"] = enabled
	special["skill_id"] = stype if enabled else ""
	special["cooldown_ms"] = 0.0
	changed.emit()

func set_special_cooldown(ms: float) -> void:
	special["cooldown_ms"] = maxf(0.0, ms)
	changed.emit()

func set_staff_equipped(v: bool) -> void:
	if staff_equipped != v:
		staff_equipped = v
		changed.emit()

func special_ready() -> bool:
	return bool(special.get("enabled", false)) and float(special.get("cooldown_ms", 0.0)) <= 0.0
