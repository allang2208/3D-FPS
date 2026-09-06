extends RefCounted
## Port of WorldEventTimelineSystem and GameUIManager clustering; seconds replace JS ms.
const Schedule := preload("res://scripts/weather_schedule.gd")
const Clock := preload("res://ui/game_clock.gd")
const WEATHER_NAMES := {"clear":"晴天","overcast":"阴天","light_rain":"小雨","rain":"中雨","storm":"暴风雨"}
const WEATHER_ICONS := {"clear":"☀","overcast":"☁","light_rain":"🌦","rain":"🌧","storm":"⛈"}
const WEATHER_IMAGES := {"light_rain":"rain-light.png","rain":"rain-moderate.png","storm":"rain-storm.png"}
var providers: Dictionary = {}
var horizon_days := 5.0
var _cache_key := ""
var _forecast: Array[Dictionary] = []

func register_provider(id: String, provider: Callable) -> bool:
	if id.is_empty() or not provider.is_valid(): return false
	providers[id] = provider
	return true

func unregister_provider(id: String) -> bool:
	return providers.erase(id)

static func absolute_time(seconds: float, day_seconds := 1440.0) -> String:
	var cycles := maxf(0,seconds)/day_seconds+Clock.START_PHASE
	var minutes := int(floor(fposmod(fposmod(cycles,1.0)*24+6,24)*60))
	return "第%d日 %02d:%02d" % [int(floor(cycles))+1,minutes/60,minutes%60]

static func time_label(event: Dictionary, now: float, day_seconds: float) -> String:
	if event.get("status","")=="active": return "进行中"
	var days: float = maxf(0,event.at-now)/day_seconds
	if days<1.0/24: return "即将发生"
	if days<1: return "%d 小时后" % ceili(days*24)
	return "%.1f 天后" % days

func weather_events(clock: RefCounted, weather: Node, world_name: String) -> Array[Dictionary]:
	if not is_instance_valid(weather): return []
	var now: float = clock.elapsed_seconds
	if not weather.automatic:
		if weather.mode not in ["light_rain","rain","storm"]: return []
		var event := _weather_event({"mode":weather.mode,"start":now,"end":now},world_name)
		event.id = "weather:manual:"+weather.mode
		event.status = "active"
		event.manual = true
		event.duration_label = "手动控制"
		event.warning_label = "手动天气，自动预报暂停"
		return [event]
	var day := int(now/clock.DAY_SECONDS)
	var key := "%d:%d:%s" % [clock.weather_seed,day,world_name]
	if key!=_cache_key:
		_cache_key = key
		_forecast.clear()
		# Include yesterday to preserve start time for clear spans crossing the boundary.
		for index in range(maxi(0,day-1),day+ceili(horizon_days)+2):
			for local in Schedule.day_plan(index,clock.weather_seed,clock.DAY_SECONDS):
				var entry := {"mode":local.mode,"start":index*clock.DAY_SECONDS+local.start,"end":index*clock.DAY_SECONDS+local.end}
				if not _forecast.is_empty() and _forecast[-1].mode==entry.mode:
					_forecast[-1].end = entry.end
				else: _forecast.append(entry)
	var events: Array[Dictionary] = []
	var groups: Array[Dictionary] = []
	for entry in _forecast:
		var wet: bool = entry.mode in ["light_rain","rain","storm"]
		if wet and not groups.is_empty() and groups[-1].wet:
			groups[-1].end = entry.end
			groups[-1].stages.append(entry)
		else:
			groups.append({"wet":wet,"start":entry.start,"end":entry.end,"stages":[entry]})
	for group in groups:
		if not group.wet or group.end<=now: continue
		var stage: Dictionary = group.stages[0]
		var storm := false
		for candidate in group.stages:
			if candidate.start<=now and candidate.end>now: stage = candidate
			if candidate.mode=="storm": storm = true
		var event := _weather_event({"mode":stage.mode,"start":group.start,"end":group.end},world_name)
		event.status = "active" if group.start<=now else "upcoming"
		event.id = "weather:process:%.3f" % group.start
		event.stages = group.stages.duplicate(true)
		event.process_name = ("降雨 · 有雷暴" if storm else "降雨") if group.wet else WEATHER_NAMES[stage.mode]
		event.label = world_name+" · "+event.process_name
		if event.status=="upcoming" and group.stages.size()>1: event.intensity_name = "雨势有变化"
		if group.wet:
			event.warning_label = "本轮降雨包含雷暴，请留意雨势变化" if storm else "本轮降雨结束后转为阴天"
			if storm:
				event.warning_level = "critical"
				if event.status!="active": event.icon_path = "res://assets/ui/event-icons/rain-storm.png"
		events.append(event)
		break # One current or next rain event per region, not every forecast stage.
	return events

func _weather_event(entry: Dictionary, world_name: String) -> Dictionary:
	var kind: String = entry.mode
	var event := {"id":"weather:%s:%.3f" % [kind,entry.start],"type":"weather","type_label":"天气",
		"label":world_name+" · "+WEATHER_NAMES[kind],"world_name":world_name,"mode":kind,
		"intensity_name":WEATHER_NAMES[kind],"icon":WEATHER_ICONS[kind],"at":entry.start,
		"start":entry.start,"end":entry.end,"status":"upcoming",
		"duration_label":"%.1f 小时" % ((entry.end-entry.start)/60.0),
		"warning_level":"critical" if kind=="storm" else "",
		"warning_label":"雷暴、强风，建议寻找遮蔽" if kind=="storm" else "无降雨" if kind in ["clear","overcast"] else "降雨持续，雨势将按预报变化"}
	if WEATHER_IMAGES.has(kind): event.icon_path = "res://assets/ui/event-icons/"+WEATHER_IMAGES[kind]
	return event

func get_hud_model(clock: RefCounted, weather: Node, world_name := "当前区域") -> Dictionary:
	var now: float = clock.elapsed_seconds
	var duration: float = clock.DAY_SECONDS*horizon_days
	var entries := weather_events(clock,weather,world_name)
	var frame := {"now":now,"start":now,"end":now+duration,"duration":duration}
	for id in providers:
		var provider: Callable = providers[id]
		if not provider.is_valid(): continue
		var supplied = provider.call(frame)
		if supplied is Array:
			for event in supplied:
				if event is Dictionary: entries.append(event.duplicate(true))
	var events: Array[Dictionary] = []
	for source in entries:
		if not source.has("id") or not source.has("at") or not is_finite(source.at): continue
		var event: Dictionary = source.duplicate(true)
		if event.get("status","")!="active" and (event.at<now or event.at>now+duration): continue
		event.position = 0.04+clampf((event.at-now)/duration,0,1)*0.94
		event.type = event.get("type","generic")
		event.type_label = event.get("type_label",event.type)
		event.time_label = time_label(event,now,clock.DAY_SECONDS)
		event.starts_at_label = absolute_time(event.get("start",event.at),clock.DAY_SECONDS)
		event.ends_at_label = absolute_time(event.end,clock.DAY_SECONDS) if event.has("end") and not event.get("manual",false) else "—"
		events.append(event)
	events.sort_custom(func(a,b): return a.at<b.at if a.at!=b.at else str(a.id)<str(b.id))
	return {"now_position":0.04,"duration_days":horizon_days,"events":events}

static func cluster_events(events: Array) -> Array:
	var groups: Array = []
	for event in events:
		if groups.is_empty() or event.position-groups[-1][0].position>0.08: groups.append([event])
		else: groups[-1].append(event)
	var result: Array = []
	for group in groups:
		if group.size()<=2:
			result.append_array(group)
			continue
		var position_sum := 0.0
		var active := false
		var ids: Array[String] = []
		var labels := {}
		for event in group:
			position_sum += event.position
			active = active or event.get("status","")=="active"
			ids.append(str(event.id))
			labels[event.time_label] = true
		ids.sort()
		result.append({"id":"cluster:"+"|".join(ids),"type":"cluster","type_label":"事件簇",
			"label":"%d个同期事件" % group.size(),"position":position_sum/group.size(),
			"status":"active" if active else "upcoming","time_label":group[0].time_label if labels.size()==1 else "同一时段","cluster_events":group})
	return result

static func assign_lanes(events: Array) -> Array[int]:
	var last := [-INF,-INF]
	var lanes: Array[int] = []
	for event in events:
		var lane := 0 if event.position-last[0]>=0.14 else 1 if event.position-last[1]>=0.14 else 0 if last[0]<=last[1] else 1
		last[lane] = event.position
		lanes.append(lane)
	return lanes
