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
	}
	return out

func _eval(formula: String, level: int) -> float:
	var expr := String(formula).replace("level", str(level))
	var total := 0.0
	for term in expr.split("+"):
		var t := term.strip_edges()
		if t.contains("*"):
			var mul := 1.0
			for p in t.split("*"):
				mul *= float(p.strip_edges())
			total += mul
		else:
			total += float(t)
	return total
