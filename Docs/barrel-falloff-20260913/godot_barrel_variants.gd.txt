extends RefCounted
## Keep the historical foregrip save slot; short/long are statistics only.
const IDS := ["short", "long"]
const NAMES := ["短枪管", "长枪管"]
const RIFLES := ["infima_ar", "hk416", "qbz191", "m16"]

static func normalize(value: Variant) -> Variant:
	return value if value is String and value in IDS else (value is bool and value)

static func for_weapon(data: Resource, parts: Dictionary) -> Variant:
	return normalize(parts.get("foregrip", false)) if data.resource_path.get_file().get_basename() in RIFLES else false

static func ads_delta(value: Variant) -> float:
	return {"short": -0.2, "long": 0.2}.get(str(value), 0.0)

static func spread_multiplier(value: Variant) -> float:
	return {"short": 0.5, "long": 1.5}.get(str(value), 1.0)

static func range_multiplier(value: Variant) -> float:
	return {"short": 0.8, "long": 1.25}.get(str(value), 1.0)

static func recoil_multiplier(value: Variant) -> float:
	return {"short": 1.15, "long": 0.85, "true": 0.85}.get(str(value), 1.0)

static func display_name(value: Variant) -> String:
	return NAMES[IDS.find(value)] if value is String and value in IDS else "稳定型枪管"

static func effects(value: Variant) -> Array:
	if str(value) not in IDS:
		return [{"text": "降低15%后坐力及镜头抖动", "benefit": 1}] if value is bool and value else []
	var short := str(value) == "short"
	return [
		{"text": "ADS瞄准耗时减少200ms" if short else "ADS瞄准耗时增加200ms", "benefit": 1 if short else -1},
		{"text": "腰射随机扩散减少50%" if short else "腰射随机扩散增加50%", "benefit": 1 if short else -1},
		{"text": "增加15%后坐力及镜头抖动" if short else "降低15%后坐力及镜头抖动", "benefit": -1 if short else 1},
		{"text": "有效射程减少20%" if short else "有效射程增加25%", "benefit": -1 if short else 1},
	]
