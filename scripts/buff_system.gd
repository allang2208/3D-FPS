class_name BuffSystem
extends RefCounted
## 通用 Buff/状态引擎（旧版 damageable-entity.js statusEffects + status-bar.js 移植）
## 宿主（enemy/player）持有 _buffs 实例；tick(delta, host) 驱动计时与 DoT/HoT；
## 伤害修正由宿主的 take_damage 调 incoming_damage_mul 消费。

const BuffsDb := preload("res://ui/buffs_db.gd")

signal changed()
signal expired(type: String)

## 每个元素：{ type, remaining_s, duration_s, stacks, opts }
var effects: Array[Dictionary] = []

func _def(type: String) -> Dictionary:
	return BuffsDb.get_def(type)

## 添加状态：同类型刷新时长（取较大值）/覆盖层数；statusImmune 免疫其他状态入库
func add(type: String, duration_ms: float, opts := {}) -> Dictionary:
	if type != "statusImmune" and has("statusImmune"):
		return {}
	var duration_s := maxf(0.0, float(duration_ms) / 1000.0)
	var existing := _find(type)
	if not existing.is_empty():
		if opts.get("battle_remaining") != null:
			existing["remaining_s"] = -1.0
			existing["duration_s"] = -1.0
			existing["opts"]["battle_remaining"] = opts["battle_remaining"]
		else:
			existing["remaining_s"] = maxf(existing["remaining_s"], duration_s)
			existing["duration_s"] = maxf(existing["duration_s"], duration_s)
		if opts.has("stacks"):
			existing["stacks"] = maxi(1, int(opts["stacks"]))
		if opts.has("meta"):
			existing["opts"]["meta"] = opts["meta"]
		changed.emit()
		return existing
	var def := _def(type)
	var stacks := maxi(1, int(opts.get("stacks", 1)))
	var entry := {
		"type": type,
		"remaining_s": -1.0 if opts.get("battle_remaining") != null else duration_s,
		"duration_s": -1.0 if opts.get("battle_remaining") != null else duration_s,
		"stacks": stacks,
		"opts": opts.duplicate(true),
	}
	effects.append(entry)
	changed.emit()
	return entry

func _find(type: String) -> Dictionary:
	for e in effects:
		if e["type"] == type:
			return e
	return {}

func remove(type: String) -> void:
	for i in range(effects.size() - 1, -1, -1):
		if effects[i]["type"] == type:
			effects.remove_at(i)
			changed.emit()
			expired.emit(type)
			return

func has(type: String) -> bool:
	return not _find(type).is_empty()

func stacks(type: String) -> int:
	var e := _find(type)
	return int(e.get("stacks", 0)) if not e.is_empty() else 0

func remaining(type: String) -> float:
	var e := _find(type)
	if e.is_empty():
		return 0.0
	return -1.0 if e["remaining_s"] < 0.0 else e["remaining_s"]

func get_effect(type: String) -> Dictionary:
	return _find(type)

func clear() -> void:
	if effects.is_empty():
		return
	effects.clear()
	changed.emit()

## 计时 + DoT/HoT；host 需提供 take_damage(d, type, src) / heal(n) / hp / max_hp
func tick(delta: float, host: Node) -> void:
	if effects.is_empty():
		return
	var i := effects.size() - 1
	while i >= 0:
		var e: Dictionary = effects[i]
		var type: String = e["type"]
		if e["remaining_s"] >= 0.0:
			e["remaining_s"] -= delta
		var opts: Dictionary = e["opts"]
		var tick_ms := float(_def(type).get("tick_ms", 0.0))
		if tick_ms > 0.0 and host != null:
			var t := float(opts.get("tick_t", tick_ms / 1000.0))
			t -= delta
			if t <= 0.0:
				t = tick_ms / 1000.0
				opts["_last_dt"] = delta
				_tick_dot(type, e, host)
			opts["tick_t"] = t
		# 计时型效果到期移除；battle_remaining 效果 remaining_s=-1 不参与倒计时
		if e["remaining_s"] != -1.0 and e["remaining_s"] <= 0.0:
			effects.remove_at(i)
			changed.emit()
			expired.emit(type)
		i -= 1

func _tick_dot(type: String, e: Dictionary, host: Node) -> void:
	var stacks_n := maxi(1, int(e["stacks"]))
	match type:
		"burn":
			var list: Array = e["opts"].get("burn_stacks", [])
			var total := 0
			var src: Node3D = e["opts"].get("source")
			for s in list:
				s["remaining_s"] -= e["opts"].get("_last_dt", 0.0)
				if float(s.get("remaining_s", 0.0)) > 0.0:
					total += maxi(1, floori(int(s.get("matk", 0)) * float(s.get("damage_mul", 0.5))))
			if total > 0 and host.has_method("take_damage"):
				host.take_damage(total, "magic", src if src != null else host)
			list = list.filter(func(s: Dictionary) -> bool: return float(s.get("remaining_s", 0.0)) > 0.0)
			e["opts"]["burn_stacks"] = list
			e["stacks"] = maxi(1, list.size())
			if list.is_empty():
				remove("burn")
		"poison":
			if host.has_method("take_damage"):
				host.take_damage(stacks_n, "physical", e["opts"].get("source"))
		"bleed":
			var b_list: Array = e["opts"].get("bleed_stacks", [])
			for s in b_list:
				s["remaining_s"] -= float(e["opts"].get("_last_dt", 0.0))
			var hp_now := int(host.get("hp")) if host.get("hp") != null else int(host.get("_hp")) if host.get("_hp") != null else 0
			var dmg := maxi(1, floori(hp_now * 0.01))
			if host.has_method("take_damage"):
				host.take_damage(dmg, "physical", e["opts"].get("source"))
			b_list = b_list.filter(func(s: Dictionary) -> bool: return float(s.get("remaining_s", 0.0)) > 0.0)
			e["opts"]["bleed_stacks"] = b_list
			e["stacks"] = maxi(1, b_list.size())
			if b_list.is_empty():
				remove("bleed")
		"holyRenewal":
			if host.has_method("heal"):
				var mhp := int(host.get("max_hp")) if host.get("max_hp") != null else 100
				host.heal(maxi(1, floori(mhp * 0.01 * stacks_n)))

## 移动速度倍率：寒冷/加速/激励/恐惧（层数加法叠加，最终乘算）
func speed_mul() -> float:
	var m := 1.0
	var chill := _find("chill")
	if not chill.is_empty():
		var per := float(_def("chill").get("stacks_mult", 0.05))
		m *= maxf(0.0, 1.0 - int(chill["stacks"]) * per)
	var haste := _find("haste")
	if not haste.is_empty():
		var per2 := float(_def("haste").get("per_stack", 0.10))
		m *= 1.0 + int(haste["stacks"]) * per2
	var inspire := _find("inspire")
	if not inspire.is_empty():
		m *= float(inspire["opts"].get("speed_mul", 1.33))
	var fear := _find("fear")
	if not fear.is_empty():
		m *= maxf(0.01, 1.0 - int(fear["stacks"]) * 0.33)
	return maxf(0.01, m)

## 物理攻击倍率（激励）
func atk_mul() -> float:
	var inspire := _find("inspire")
	if inspire.is_empty():
		return 1.0
	return float(inspire["opts"].get("atk_mul", 1.5))

## 受击伤害倍率：魔力易伤/感电/无人机易伤/冻结（冻结只对非魔法伤害生效）
func incoming_damage_mul(damage_type: String) -> float:
	var m := 1.0
	if damage_type == "magic" or damage_type == "electric":
		var mv := _find("magicVulnerability")
		if not mv.is_empty():
			m *= 1.0 + int(mv["stacks"]) * float(_def("magicVulnerability").get("stacks_mult", 0.05))
	if damage_type == "electric":
		var el := _find("electrified")
		if not el.is_empty():
			m *= 1.0 + int(el["stacks"]) * float(_def("electrified").get("stacks_mult", 0.03))
	var dv := _find("droneVulnerability")
	if not dv.is_empty():
		m *= 1.0 + int(dv["stacks"]) * float(_def("droneVulnerability").get("stacks_mult", 0.10))
	if damage_type != "magic" and damage_type != "electric":
		var fz := _find("frozen")
		if not fz.is_empty():
			m *= 1.0 + float(_def("frozen").get("physical_bonus", 0.5))
	return m

## 控制锁：眩晕/冻结期间不可行动（恐惧由 AI 另行处理为逃跑）
func is_control_locked() -> bool:
	return has("stun") or has("frozen")

func effect_snapshot() -> Array[Dictionary]:
	var out: Array[Dictionary] = []
	for e in effects:
		var def := _def(e["type"])
		out.append({
			"type": e["type"],
			"icon": def["icon"],
			"name": def["name"],
			"color": def["color"],
			"desc": def["desc"],
			"remaining_s": e["remaining_s"],
			"duration_s": e["duration_s"],
			"stacks": e["stacks"],
			"battle_remaining": e["opts"].get("battle_remaining"),
		})
	return out
