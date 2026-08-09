extends RefCounted
## 技能库（从旧版 data/skills.json 迁移）：加载全量定义，图标重映射到 skills 目录。
## 技能效果按旧版 effectFormula 在 effect(id, level) 中计算，供施法系统使用。

const SKILLS_JSON := "res://assets/data/skills.json"
const SKILL_ICON_DIRS := [
	"res://assets/ui/icons/skills/",
	"res://assets/ui/icons/",
]

var skills := {}  # id -> 定义（含重映射后的 icon）

func _init() -> void:
	var f := FileAccess.open(SKILLS_JSON, FileAccess.READ)
	if f == null:
		return
	var data = JSON.parse_string(f.get_as_text())
	f.close()
	if not (data is Dictionary) or not data.has("skills"):
		return
	var all: Dictionary = data["skills"]
	for id in all.keys():
		var def: Dictionary = all[id].duplicate(true)
		var icon_path := String(def.get("iconImage", ""))
		var mapped := ""
		if icon_path != "":
			for dir in SKILL_ICON_DIRS:
				var candidate: String = dir + icon_path.get_file()
				if ResourceLoader.exists(candidate):
					mapped = candidate
					break
		def["icon"] = mapped if mapped != "" else String(def.get("icon", ""))
		skills[id] = def

func has_skill(id: String) -> bool:
	return skills.has(id)

func get_def(id: String) -> Dictionary:
	return skills.get(id, {})

## 原始 effectFormula 全量求值（技能实现直接取各自字段）
func effect_raw(id: String, level := 1) -> Dictionary:
	var def := get_def(id)
	if def.is_empty():
		return {}
	var f: Dictionary = def.get("effectFormula", {})
	var out := {}
	for k in f.keys():
		out[k] = _eval(f[k], level)
	return out

func exp_formula(id: String) -> String:
	return String(get_def(id).get("expFormula", "100"))

func exp_rewards(id: String) -> Dictionary:
	return get_def(id).get("expRewards", {})

func sounds(id: String) -> Dictionary:
	return get_def(id).get("sounds", {})

## 按旧版 effectFormula 计算某等级效果（字符串公式求值：base + level * mul）
func effect(id: String, level := 1) -> Dictionary:
	var def := get_def(id)
	if def.is_empty():
		return {}
	var f: Dictionary = def.get("effectFormula", {})
	var out := {
		"damage_base": _eval(f.get("damageBase", "0"), level),
		"magic_mul": _eval(f.get("magicMul", "0"), level),
		"int_mul": _eval(f.get("intMul", "0"), level),
		"cooldown_s": float(f.get("cooldown", 0.0)),
		"mp_cost": int(f.get("mpCost", 0)),
		"explosion_radius_m": _eval(f.get("explosionRadius", "1"), level) * 0.014,
		"fly_speed_m": float(f.get("flySpeed", 0.0)) * 0.014,
		"max_range_m": float(f.get("maxRange", 0.0)) * 0.014,
		"duration_s": float(f.get("duration", 0.0)),
		# 冰锥：多投射物数量
		"spike_count": int(_eval(f.get("spikeCount", "1"), level)),
		# 闪电：锁定/传导
		"aim_radius_m": _eval(f.get("aimRadius", "0"), level) * 0.014,
		"chain_range_m": _eval(f.get("chainRange", "0"), level) * 0.014,
		"chain_targets": int(_eval(f.get("chainTargets", "1"), level)),
		"chain_decay": float(f.get("chainDecay", 0.0)),
		"stun_ms": _eval(f.get("stunMs", "0"), level),
		"electrify_stacks": int(_eval(f.get("electrifyStacks", "1"), level)),
		"electrify_duration_ms": _eval(f.get("electrifyDurationMs", "0"), level),
		"fade_ms": float(f.get("fadeMs", 0.0)),
		"segments": int(f.get("segments", 10)),
		"jitter": float(f.get("jitter", 0.09)),
	}
	return out

func _eval(formula, level: int) -> float:
	if formula is int or formula is float:
		return float(formula)
	var expr_str := String(formula)
	expr_str = expr_str.replace("Math.floor", "floor")
	expr_str = expr_str.replace("Math.round", "round")
	expr_str = expr_str.replace("Math.PI", "pi")
	var expr := Expression.new()
	var err := expr.parse(expr_str, ["level"])
	if err != OK:
		return 0.0
	var result = expr.execute([float(level)])
	if expr.has_execute_failed():
		return 0.0
	return float(result)
