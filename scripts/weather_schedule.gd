extends RefCounted
## Reproducible fronts targeting ~40% rainy scheduled time over many days.
## Durations are real seconds at a 24-minute day; dry breaks remain mandatory.
static func day_plan(day: int, seed_value: int, day_seconds := 1440.0) -> Array[Dictionary]:
	var rng := RandomNumberGenerator.new()
	rng.seed = hash("weather-v1:%d:%d" % [seed_value,day])
	var plan: Array[Dictionary] = []
	var cursor := 0.0
	var scale := day_seconds/1440.0
	# Each front must fit completely; reserve a dry end so midnight never cuts off a storm.
	while cursor<day_seconds:
		var front: Array[Dictionary] = []
		front.append({"mode":"clear","duration":rng.randf_range(70,120)*scale})
		front.append({"mode":"overcast","duration":rng.randf_range(30,50)*scale})
		if rng.randf()<0.9:
			front.append({"mode":"light_rain","duration":rng.randf_range(85,115)*scale})
			if rng.randf()<0.8:
				front.append({"mode":"rain","duration":rng.randf_range(55,85)*scale})
				if rng.randf()<0.28:
					front.append({"mode":"storm","duration":rng.randf_range(30,55)*scale})
					front.append({"mode":"rain","duration":rng.randf_range(25,40)*scale})
				front.append({"mode":"light_rain","duration":rng.randf_range(25,35)*scale})
			front.append({"mode":"overcast","duration":rng.randf_range(30,50)*scale})
		var length := 0.0
		for entry in front: length += entry.duration
		if cursor+length>day_seconds-90*scale:
			plan.append({"mode":"clear","start":cursor,"end":day_seconds})
			break
		for entry in front:
			plan.append({"mode":entry.mode,"start":cursor,"end":cursor+entry.duration})
			cursor += entry.duration
	return plan

static func state_at(elapsed: float, seed_value: int, day_seconds := 1440.0) -> Dictionary:
	var day := int(maxf(0,elapsed)/day_seconds)
	var local_time := fposmod(maxf(0,elapsed),day_seconds)
	for entry in day_plan(day,seed_value,day_seconds):
		if local_time<entry.end:
			return {"mode":entry.mode,"until":day*day_seconds+entry.end}
	return {"mode":"clear","until":(day+1)*day_seconds}
