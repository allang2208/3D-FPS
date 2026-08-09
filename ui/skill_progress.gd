extends RefCounted
## 技能修炼系统（旧版 SkillLevelSystem / SkillManager 经验侧迁移）
## 每个技能维护 level/exp/max_exp：施法命中/击杀/多杀按 expRewards 加经验，
## exp 满 max_exp 升级（expFormula 求值），满级清零。changed 信号驱动面板刷新。

signal changed

var _db
var _progress := {}  # skill_id -> {level:int, exp:float, max_exp:float}

func _init(db) -> void:
	_db = db

func has(id: String) -> bool:
	return _progress.has(id)

func get_level(id: String) -> int:
	return int(_progress.get(id, {}).get("level", 1))

func get_exp(id: String) -> float:
	return float(_progress.get(id, {}).get("exp", 0.0))

func get_max_exp(id: String) -> float:
	return float(_progress.get(id, {}).get("max_exp", 100.0))

func ensure(id: String) -> void:
	if _progress.has(id):
		return
	_progress[id] = {"level": 1, "exp": 0.0, "max_exp": _exp_for(id, 1)}

## 施法结算：按 expRewards 加经验（hit/kill/multiHit/multiKill）
func award(id: String, hits: int, kills: int) -> bool:
	if hits <= 0 and kills <= 0:
		return false
	ensure(id)
	var rw: Dictionary = _db.exp_rewards(id)
	var gained := 0.0
	gained += float(rw.get("hit", 0)) * maxi(0, hits)
	gained += float(rw.get("kill", 0)) * maxi(0, kills)
	if hits >= 2:
		gained += float(rw.get("multiHit", 0))
	if kills >= 2:
		gained += float(rw.get("multiKill", 0))
	return bool(add_exp(id, gained).get("leveled", false))

func add_exp(id: String, amount: float) -> Dictionary:
	ensure(id)
	var p: Dictionary = _progress[id]
	var max_lv := int(_db.get_def(id).get("maxLevel", 20))
	if int(p.level) >= max_lv or amount <= 0.0:
		return {"leveled": false, "level": int(p.level)}
	p.exp = float(p.exp) + amount
	var leveled := false
	while float(p.exp) >= float(p.max_exp) and int(p.level) < max_lv:
		p.exp = float(p.exp) - float(p.max_exp)
		p.level = int(p.level) + 1
		p.max_exp = _exp_for(id, int(p.level))
		leveled = true
	if int(p.level) >= max_lv:
		p.exp = 0.0
	changed.emit()
	return {"leveled": leveled, "level": int(p.level)}

func _exp_for(id: String, level: int) -> float:
	var formula := String(_db.exp_formula(id))
	var expr_str := formula.replace("Math.floor", "floor").replace("Math.round", "round")
	var expr := Expression.new()
	if expr.parse(expr_str, ["level"]) != OK:
		return 100.0
	var r = expr.execute([float(level)])
	if expr.has_execute_failed():
		return 100.0
	return float(r)
