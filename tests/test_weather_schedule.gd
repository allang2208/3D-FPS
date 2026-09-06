extends SceneTree
const Schedule := preload("res://scripts/weather_schedule.gd")
const Clock := preload("res://ui/game_clock.gd")
func _initialize() -> void:
	var totals := {"clear":0.0,"overcast":0.0,"light_rain":0.0,"rain":0.0,"storm":0.0}
	var longest_rain := 0.0
	var dry_days := 0
	for day in 1000:
		var plan := Schedule.day_plan(day,72124)
		assert(plan==Schedule.day_plan(day,72124))
		assert(plan[0].mode=="clear" and plan[-1].mode=="clear")
		var cursor := 0.0
		var wet := 0.0
		var run := 0.0
		var previous := "clear"
		for entry in plan:
			assert(is_equal_approx(entry.start,cursor))
			assert(entry.end>entry.start)
			var duration: float = entry.end-entry.start
			totals[entry.mode] += duration
			if entry.mode in ["light_rain","rain","storm"]:
				wet += duration
				run += duration
				longest_rain = maxf(longest_rain,run)
			else: run = 0.0
			if entry.mode=="storm": assert(previous=="rain")
			if previous=="storm": assert(entry.mode=="rain")
			if previous=="clear": assert(entry.mode in ["clear","overcast"])
			var state := Schedule.state_at(day*1440+entry.start+duration*.5,72124)
			assert(state.mode==entry.mode and is_equal_approx(state.until,day*1440+entry.end))
			previous = entry.mode
			cursor = entry.end
		assert(is_equal_approx(cursor,1440))
		assert(wet<1440*.7)
		if wet==0: dry_days += 1
	assert(longest_rain<=330)
	var wet_ratio: float = (totals.light_rain+totals.rain+totals.storm)/1440000
	assert(wet_ratio>=0.38 and wet_ratio<=0.42)
	for value in totals.values(): assert(value>0)
	assert(Schedule.day_plan(2,72124)!=Schedule.day_plan(2,72125))
	var clock := Clock.new()
	clock.elapsed_seconds = 9832.5
	var saved := clock.serialize()
	var restored := Clock.new()
	restored.restore(saved)
	assert(restored.weather_seed==clock.weather_seed)
	assert(Schedule.state_at(clock.elapsed_seconds,clock.weather_seed)==Schedule.state_at(restored.elapsed_seconds,restored.weather_seed))
	restored.restore({"elapsedMs":120000,"daySeconds":1440})
	assert(restored.weather_seed==72124)
	print("PASS weather schedule: 1000 days, save/restore, distinct seeds, bounded rain, dry recovery. Longest rain seconds=",longest_rain," dry days=",dry_days)
	for key in totals: print(key," percent=",snappedf(totals[key]/1440000*100,0.01))
	quit()
