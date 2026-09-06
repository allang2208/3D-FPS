extends SceneTree
const Model := preload("res://ui/event_timeline_model.gd")
const Schedule := preload("res://scripts/weather_schedule.gd")
var failures := 0
func _initialize() -> void:
	OS.set_environment("INVENTORY_SAVE_PATH","user://timeline-test-%d.save" % OS.get_process_id())
	call_deferred("run")
func check(ok: bool, message: String) -> void:
	if not ok:
		failures += 1
		printerr("TIMELINE FAIL: ",message)
func run() -> void:
	var hud := root.get_node("HUD")
	hud._ensure_built()
	hud.set_process(false)
	hud._save_queued = true
	hud.game_clock.weather_seed = 72124
	hud.game_clock.elapsed_seconds = 0
	var world := Node3D.new()
	world.name = "TimelineTestWorld"
	root.add_child(world)
	current_scene = world
	var camera := Camera3D.new()
	world.add_child(camera)
	camera.make_current()
	var env = preload("res://scripts/world_lighting.gd").create_environment()
	world.add_child(env)
	world.add_child(preload("res://scripts/world_lighting.gd").create_sun())
	for i in 4: await process_frame
	var weather = env.weather
	weather.resume_automatic()
	var ui = hud.status_bar.event_timeline
	ui.refresh()
	check(ui.compact,"starts compact")
	ui._toggle.pressed.emit()
	check(not ui.compact,"expand button signal wired")
	ui.set_compact(true,false)
	check(ui._window.get_theme_font("font")==preload("res://ui/style.gd").make_font(),"caption uses current regular SimHei")
	check(ui.current_events.size()>0,"forecast populated from live world")
	check(ui.current_events.size()==1,"only nearest rain event appears")
	check(ui.display_events.size()==1 and ui._markers.size()==1,"original progress bar has one weather marker")
	var previous_id := ""
	var previous_end := 0.0
	for seconds in range(0,3000,17):
		hud.game_clock.elapsed_seconds = seconds
		var forecast: Array = ui.model.weather_events(hud.game_clock,weather,"测试区域")
		check(forecast.size()==1,"only current or nearest upcoming rain across day boundary")
		var event: Dictionary = forecast[0]
		check(event.mode in ["light_rain","rain","storm"],"dry weather is not an event")
		check(event.end>seconds,"finished rain is removed")
		if seconds<previous_end:
			check(event.id==previous_id,"rain intensity changes preserve the same event")
		previous_id = event.id
		previous_end = event.end
		var actual: Dictionary = Schedule.state_at(seconds,hud.game_clock.weather_seed)
		if event.start<=seconds:
			check(event.status=="active" and event.mode==actual.mode,"active marker matches actual rain intensity")
		else:
			check(event.status=="upcoming" and actual.mode in ["clear","overcast"],"dry periods forecast the next rain")
		for i in event.stages.size():
			var stage: Dictionary = event.stages[i]
			check(stage.mode in ["light_rain","rain","storm"],"only continuous rain stages are merged")
			check(Schedule.state_at((stage.start+stage.end)*0.5,hud.game_clock.weather_seed).mode==stage.mode,"stage matches actual schedule")
			if i>0: check(is_equal_approx(event.stages[i-1].end,stage.start),"rain stages are contiguous")
	hud.game_clock.elapsed_seconds = 0
	ui.refresh()
	for event in ui.current_events:
		for stage in event.stages:
			var middle: float = (stage.start+stage.end)*0.5
			check(Schedule.state_at(middle,hud.game_clock.weather_seed).mode==stage.mode,"each rain stage matches actual schedule")
		if event.mode in ["rain","light_rain","storm"]: check(ResourceLoader.exists(event.icon_path),"original PNG exists")
	check(Model.absolute_time(0)=="第1日 12:00","matches existing clock")
	var sample := [{"id":"a","position":0.2,"time_label":"1小时后","status":"upcoming","type":"weather"},{"id":"b","position":0.23,"time_label":"1小时后","status":"upcoming","type":"weather"},{"id":"c","position":0.27,"time_label":"1小时后","status":"active","type":"weather"}]
	var clustered := Model.cluster_events(sample)
	check(clustered.size()==1 and clustered[0].cluster_events.size()==3,"source three-event cluster rule")
	check(clustered[0].status=="active","cluster preserves active status")
	check(Model.cluster_events(sample.slice(0,2)).size()==2,"two events remain separate")
	check(Model.assign_lanes(sample)==[0,1,0],"source two-lane assignment")
	ui.model.register_provider("test",func(frame): return [{"id":"invasion-test","type":"invasion","type_label":"入侵","at":frame.now+300,"label":"测试入侵","status":"upcoming","icon_path":"res://assets/ui/event-icons/invasion.png"}])
	ui.refresh()
	ui.set_filter("invasion")
	check(ui.display_events.size()==1 and ui.display_events[0].type=="invasion","type filter works")
	ui.model.unregister_provider("test")
	ui.refresh()
	check(ui.filter_type=="all","removed type resets filter")
	var calls := [0]
	ui.set_invasion_model({"text":"测试入侵","active":true,"can_support":true,"severity":"critical"},func(): calls[0]+=1)
	check(ui._support.visible and not ui._support.disabled,"support available only with callable")
	ui._support.pressed.emit()
	check(calls[0]==1,"support calls provider action")
	ui.set_invasion_model({"text":"暂无入侵情报","active":false})
	for resolution in [Vector2i(1920,1080),Vector2i(1280,720),Vector2i(960,540)]:
		root.size = resolution
		await process_frame
		ui.set_compact(false,false)
		for i in 4: await process_frame
		check(Rect2(Vector2.ZERO,Vector2(resolution)).encloses(ui._panel.get_global_rect()),"panel fits "+str(resolution))
		check(not ui._panel.get_global_rect().intersects(hud.status_bar._clock_view.get_global_rect()),"clock does not overlap "+str(resolution))
		for event in ui.display_events:
			if event.has("cluster_events"):
				ui._show_event(event)
				check(ui._popover.visible,"cluster opens")
				var child_id: int = ui._popover_content.get_child(0).get_instance_id()
				hud.game_clock.elapsed_seconds += 0.1
				ui.refresh()
				check(ui._popover_content.get_child(0).get_instance_id()==child_id,"moving positions do not reset cluster scrolling")
				break
		for i in 4: await process_frame

		var weather_event: Dictionary = ui.current_events[0]
		ui._markers[0].pressed.emit()
		check(ui._popover.visible,"weather marker opens details")
		ui.close_popover()
		ui._show_event(weather_event)
		check(ui._popover_title.text=="天气预报详情","marker opens weather details")
		for i in 4: await process_frame
		check(Rect2(Vector2.ZERO,Vector2(resolution)).encloses(ui._popover.get_global_rect()),"popover fits "+str(resolution))
		ui._show_event(weather_event)
		check(not ui._popover.visible,"same event toggles closed")
		ui._show_event(weather_event)
		var key := InputEventKey.new()
		key.pressed = true
		key.keycode = KEY_ESCAPE
		ui._input(key)
		check(not ui._popover.visible,"escape closes details")
		ui._show_event(weather_event)
		ui.set_compact(true,false)
		check(not ui._popover.visible,"collapse closes details")
	# No fake future forecast while the weather is manually overridden.
	weather.set_weather("storm",true)
	ui.refresh()
	check(ui.current_events.size()==1 and ui.current_events[0].manual,"manual weather pauses forecast")
	weather.set_weather("clear",true)
	ui.refresh()
	check(ui.current_events.is_empty(),"manual clear weather creates no event")
	weather.resume_automatic()
	hud.game_clock.elapsed_seconds = 1450
	ui.refresh()
	check(ui.current_events.size()==1 and ui.current_events[0].end>1450,"next day keeps live forecast")
	ui._weather = null
	ui.model.providers.clear()
	var empty: Dictionary = ui.model.get_hud_model(hud.game_clock,null)
	check(empty.events.is_empty(),"no provider means empty state")
	var other := Node3D.new()
	root.add_child(other)
	current_scene = other
	ui.refresh()
	check(ui.current_events.is_empty() and not ui._popover.visible,"scene change clears old forecast and popover")
	print("TIMELINE TEST failures=",failures)
	quit(1 if failures else 0)
