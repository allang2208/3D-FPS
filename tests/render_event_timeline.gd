extends SceneTree
const OUTPUT := "res://docs/preview/weather-event-bar"
func _initialize() -> void:
	OS.set_environment("INVENTORY_SAVE_PATH","user://timeline-render-%d.save" % OS.get_process_id())
	call_deferred("run")
func capture(name: String) -> void:
	for i in 8: await process_frame
	await RenderingServer.frame_post_draw
	root.get_texture().get_image().save_png(OUTPUT.path_join(name+".png"))
func run() -> void:
	DirAccess.make_dir_recursive_absolute(OUTPUT)
	var scene_path: String = "res://scenes/sky_base/sky_base.tscn" if ResourceLoader.exists("res://scenes/sky_base/sky_base.tscn") else ProjectSettings.get_setting("application/run/main_scene")
	var world = load(scene_path).instantiate()
	var hud := root.get_node("HUD")
	hud._ensure_built()
	root.add_child(world)
	current_scene = world
	for i in 35: await process_frame
	hud.set_process(false)
	hud._save_queued = true
	hud.game_clock.weather_seed = 72124
	hud.game_clock.elapsed_seconds = 0
	var player: Node = world.find_child("Player",true,false)
	if player != null: player.set_physics_process(false)
	var camera := Camera3D.new()
	world.add_child(camera)
	camera.far = 4000
	camera.position = Vector3(8,3,11)
	camera.look_at(Vector3(-8,7,-12))
	camera.make_current()
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	var timeline = hud.status_bar.event_timeline
	timeline.reduced_motion = true
	timeline.refresh()
	var file := FileAccess.open(OUTPUT.path_join("fixture.json"),FileAccess.WRITE)
	file.store_string(JSON.stringify(timeline.current_events,"  "))
	file.close()
	for resolution in [Vector2i(1920,1080),Vector2i(1280,720),Vector2i(960,540)]:
		root.size = resolution
		for i in 5: await process_frame
		timeline.set_compact(true,false)
		await capture("compact-%d" % resolution.x)
		timeline.set_compact(false,false)
		await capture("expanded-%d" % resolution.x)
		for event in timeline.current_events:
			if event.get("stages",[]).size()>1:
				timeline._show_event(event)
				break
		if not timeline._popover.visible and not timeline.current_events.is_empty():
			timeline._show_event(timeline.current_events[0])
		await capture("forecast-%d" % resolution.x)
		assert(timeline._popover.get_global_rect().end.x<=resolution.x)
		assert(timeline._popover.get_global_rect().end.y<=resolution.y)
		print("TIMELINE_RENDER ",resolution," panel=",timeline._panel.get_global_rect()," popover=",timeline._popover.get_global_rect())
	quit()
