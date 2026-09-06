extends RefCounted
## 现实24分钟一日，1分钟对应游戏1小时；phase=0为06:00，初始正午。
var elapsed_seconds := 0.0
var weather_seed: int = randi_range(1,2147483646)
const DAY_SECONDS := 1440.0
const START_PHASE := 0.25

func advance(delta: float) -> void:
	elapsed_seconds += maxf(0, delta)

func model() -> Dictionary:
	var cycles := elapsed_seconds / DAY_SECONDS + START_PHASE
	var phase := fposmod(cycles, 1.0)
	var minutes := int(floor(fposmod(phase * 24.0 + 6.0, 24.0) * 60.0))
	var hour := floori(minutes / 60.0)
	var period := "深夜"
	var icon := "🌙"
	if hour >= 5 and hour < 8:
		period = "晨曦"
		icon = "🌅"
	elif hour >= 8 and hour < 17:
		period = "白昼"
		icon = "☀"
	elif hour >= 17 and hour < 20:
		period = "黄昏"
		icon = "🌇"
	return {"day": int(floor(cycles)) + 1, "hour": hour, "minute": minutes % 60, "phase": phase, "period": period, "icon": icon}

func serialize() -> Dictionary:
	return {"elapsedMs": elapsed_seconds * 1000.0, "daySeconds": DAY_SECONDS, "weatherSeed": weather_seed}

func restore(data: Dictionary) -> void:
	# Old saves use a stable fallback; new worlds receive their own random weather.
	weather_seed = int(data.get("weatherSeed",72124))
	elapsed_seconds = maxf(0, data.get("elapsedMs", 0.0) / 1000.0)
	# Preserve the displayed time/day when loading saves from the old 12-minute cycle.
	var saved_day_seconds: float = data.get("daySeconds", 720.0)
	if saved_day_seconds > 0.0:
		elapsed_seconds *= DAY_SECONDS / saved_day_seconds
