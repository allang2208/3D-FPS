extends RefCounted
## 武器攻击公式（旧版 attack-formula.js 移植）：强化/改造/附魔后武器攻击统一计算。
## atk = base + el*enhanceFlat + Σ attr.val*(attrBase + attrPerEnhance*el)，四舍五入；
## 无 attackFormula 时从 stats「12-18」推断 base=12、enhanceFlat=1（旧版兜底）。

static func get_attack_formula(item: Dictionary) -> Dictionary:
	var formula: Dictionary = item.get("attackFormula", {})
	if not formula.is_empty():
		return formula
	var stats: Array = item.get("stats", [])
	for s in stats:
		if typeof(s) != TYPE_DICTIONARY:
			continue
		if not String(s.get("name", "")).contains("物理攻击"):
			continue
		var m := RegEx.new()
		m.compile("(\\d+)\\s*-\\s*(\\d+)")
		var res := m.search(String(s.get("value", "")))
		if res:
			return {"base": int(res.get_string(1)), "enhanceFlat": 1, "attrs": []}
	return {}

static func compute_weapon_atk(item: Dictionary, el: int, attrs: Dictionary) -> int:
	var formula := get_attack_formula(item)
	if formula.is_empty():
		return 0
	var atk := float(formula.get("base", 0)) + el * float(formula.get("enhanceFlat", 0))
	for a in formula.get("attrs", []):
		if typeof(a) != TYPE_DICTIONARY:
			continue
		var val := float(attrs.get(String(a.get("key", "")), 0))
		atk += val * (float(a.get("base", 0)) + float(a.get("perEnhance", 0)) * el)
	return roundi(atk)

## 公式展示文本（buildFormulaDisplay 对齐，强化等级 el）
static func formula_text(item: Dictionary, el: int) -> String:
	var formula := get_attack_formula(item)
	if formula.is_empty():
		return ""
	var base := int(round(float(formula.get("base", 0)) + el * float(formula.get("enhanceFlat", 0))))
	var parts: Array = [str(base)]
	var names := {"str": "力量", "dex": "敏捷", "int": "智力", "con": "体质", "wis": "精神", "luck": "幸运"}
	for a in formula.get("attrs", []):
		if typeof(a) != TYPE_DICTIONARY:
			continue
		var coeff := float(a.get("base", 0)) + float(a.get("perEnhance", 0)) * el
		if absf(coeff) < 0.001:
			continue
		var sign := "+" if coeff >= 0 else "-"
		parts.append("%s %s×%.2f" % [sign, String(names.get(String(a.get("key", "")), String(a.get("key", "")))), absf(coeff)])
	return " ".join(parts)

## 物品实例 -> 枪械生效 mods：强化 flat 伤害 + 改造/附魔 effects（未映射键原样保留）
static func gun_mods_from_item(item: Dictionary) -> Dictionary:
	var mods := {}
	var el := int(item.get("enhanceLevel", 0))
	if el > 0:
		var formula := get_attack_formula(item)
		var flat := float(formula.get("enhanceFlat", 1))
		mods["enhance_flat_damage"] = roundi(el * flat)
	var craft: Dictionary = item.get("_craftEffects", {})
	for k in craft:
		mods[k] = craft[k]
	var enchant: Dictionary = item.get("_enchantEffects", {})
	for k in enchant:
		if mods.has(k) and typeof(mods[k]) == TYPE_FLOAT and typeof(enchant[k]) == TYPE_FLOAT:
			# 改造+附魔同键数值（如伤害%）合并：1-(1+a)(1+b)
			mods[k] = (1.0 + float(mods[k])) * (1.0 + float(enchant[k])) - 1.0
		else:
			mods[k] = enchant[k]
	# 旧版 craft magazineDelta = 备弹增量，映射到 reserveDelta 供枪械生效
	if mods.has("magazineDelta") and not mods.has("reserveDelta"):
		mods["reserveDelta"] = mods["magazineDelta"]
	mods.erase("magazineDelta")
	return mods
