extends SceneTree
func _initialize() -> void:
	OS.set_environment("INVENTORY_SAVE_PATH","user://weather-review-%d.save" % OS.get_process_id())
	call_deferred("run")
func run() -> void:
	var hud := root.get_node("HUD")
	hud._ensure_built()
	hud._save_queued = true
	var scene_path: String = "res://scenes/sky_base/sky_base.tscn" if ResourceLoader.exists("res://scenes/sky_base/sky_base.tscn") else ProjectSettings.get_setting("application/run/main_scene")
	var world = load(scene_path).instantiate()
	root.add_child(world)
	current_scene = world
	for i in 25: await process_frame
	var player: Node = world.find_child("Player",true,false)
	if player != null: player.set_physics_process(false)
	if player != null: player.set_process_unhandled_input(false)
	var camera := Camera3D.new()
	camera.far = 4000
	camera.fov = 72
	world.add_child(camera)
	camera.position = Vector3(8,3,11)
	camera.look_at(Vector3(-8,7,-12))
	camera.make_current()
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	hud.set_process(false)
	hud.game_clock.elapsed_seconds = 0
	for layer in root.find_children("*","CanvasLayer",true,false): layer.hide()
	var env = world.get_node("WorldEnvironment")
	var weather = env.weather
	var output := "res://docs/preview/weather-runtime"
	DirAccess.make_dir_recursive_absolute(output)
	for mode in ["clear","overcast","light_rain","rain","storm"]:
		weather.set_weather(mode,true)
		env.refresh()
		for i in 40: await process_frame
		await RenderingServer.frame_post_draw
		assert(root.get_texture().get_image().save_png(output.path_join(mode+".png"))==OK)
		print("WEATHER_CAPTURE ",mode," sun_energy=",env.sun.light_energy," cloud=",weather.cloud_opacity(env.current_state.direction)," rain=",weather.rain.amount_ratio," sheltered=",weather.sheltered)
		if OS.get_cmdline_user_args().has("--benchmark"):
			var samples: Array[float] = []
			for sample_index in 40:
				var start := Time.get_ticks_usec()
				await process_frame
				RenderingServer.force_draw()
				root.get_texture().get_image()
				samples.append((Time.get_ticks_usec()-start)/1000.0)
			samples.sort()
			print("WEATHER_READBACK_BENCH ",mode," median_ms=",samples[20]," p95_ms=",samples[38])
	weather.trigger_lightning()
	await process_frame
	await RenderingServer.frame_post_draw
	assert(root.get_texture().get_image().save_png(output.path_join("lightning.png"))==OK)
	if OS.get_cmdline_user_args().has("--motion"):
		DirAccess.make_dir_recursive_absolute(output.path_join("frames"))
		for frame in 480:
			if frame==120: weather.trigger_lightning()
			await process_frame
			await RenderingServer.frame_post_draw
			assert(root.get_texture().get_image().save_png(output.path_join("frames/%03d.png" % frame))==OK)
	quit()
