extends SceneTree
const Weather := preload("res://scripts/weather_system.gd")
func _initialize() -> void:
	OS.set_environment("INVENTORY_SAVE_PATH","user://weather-test-%d.save" % OS.get_process_id())
	call_deferred("run")
func run() -> void:
	var hud := root.get_node("HUD")
	hud._ensure_built()
	hud.set_process(false)
	var world := Node3D.new()
	root.add_child(world)
	current_scene = world
	var camera := Camera3D.new()
	world.add_child(camera)
	camera.position = Vector3(0,2,0)
	camera.make_current()
	var lighting := preload("res://scripts/world_lighting.gd")
	var env = lighting.create_environment()
	world.add_child(env)
	world.add_child(lighting.create_sun())
	await process_frame
	await process_frame
	var weather = env.weather
	assert(Weather.scheduled_mode(0,1440)=="clear")
	assert(Weather.scheduled_mode(1440,1440)=="clear")
	assert(not weather.set_weather("invalid"))
	weather.set_weather("clear",true)
	env.refresh()
	assert(weather.cloud_opacity(Vector3.UP)==0)
	var clear_energy: float = env.sun.light_energy
	weather.set_weather("overcast",true)
	env.refresh()
	assert(env.sun.light_energy<clear_energy)
	var drizzle_mix := Weather.rain_audio_targets(Weather.PROFILES.light_rain.y)
	var medium_mix := Weather.rain_audio_targets(Weather.PROFILES.rain.y)
	var storm_mix := Weather.rain_audio_targets(Weather.PROFILES.storm.y)
	assert(drizzle_mix.z>drizzle_mix.x and drizzle_mix.y==0.0)
	assert(medium_mix.y>medium_mix.x and medium_mix.length()>drizzle_mix.length()*2.0)
	assert(storm_mix.is_equal_approx(Vector3(0.52,0.38,0.0)))
	assert(is_equal_approx(Weather.PROFILES.rain.y,0.65))
	for mode in ["light_rain","rain","storm"]:
		weather.set_weather(mode,true)
		weather._process(0.3)
		assert(weather.rain.amount==1200)
		assert(weather.rain.amount_ratio==weather.profile.y)
		assert(weather.rain_audio.playing)
	for player in [weather.rain_audio,weather.rain_detail_audio,weather.rain_drizzle_audio]:
		assert(player.stream.format==AudioStreamWAV.FORMAT_16_BITS)
		assert(player.stream.stereo)
		assert(player.stream.loop_end==529200)
		assert(is_equal_approx(player.stream.get_length(),24.0))
	weather.rain_audio.play(23.8)
	await create_timer(0.65).timeout
	assert(weather.rain_audio.playing)
	assert(weather.rain_audio.get_playback_position()<2.0)
	weather.trigger_lightning()
	assert(weather.bolt.mesh.get_surface_count()==1)
	assert(weather.flash_remaining>0)
	assert(weather.thunder_delay>=300.0/343 and weather.thunder_delay<=900.0/343)
	weather._process(0.02)
	assert(weather.flash_light.light_energy>0)
	var delay: float = weather.thunder_delay
	paused = true
	await process_frame
	await process_frame
	assert(weather.thunder_delay==delay)
	paused = false
	weather.thunder_delay = 0.02
	weather._process(0.05)
	assert(weather.thunder.playing and weather.thunder_delay<0)
	assert(weather.thunder.stream.resource_path.contains("thunder_wilderness_"))
	assert(weather.thunder.stream.stereo)
	assert(is_equal_approx(weather.thunder.stream.get_length(),11.0))
	assert(weather.thunder.stream.loop_mode==AudioStreamWAV.LOOP_DISABLED)
	weather._process(0.25)
	assert(weather.bolt.visible and weather.flash_remaining>0)
	weather._process(0.8)
	assert(not weather.bolt.visible)
	weather.set_weather("clear",true)
	weather._process(6.0)
	assert(weather.thunder_delay<0 and not weather.thunder.playing)
	assert(not weather.rain.emitting and not weather.rain_audio.playing)
	assert(weather.flash_light.light_energy==0 and not weather.bolt.visible)
	# Physical roof shelter test.
	var roof := StaticBody3D.new()
	var shape := CollisionShape3D.new()
	shape.shape = BoxShape3D.new()
	shape.shape.size = Vector3(10,0.4,10)
	roof.add_child(shape)
	world.add_child(roof)
	roof.position = Vector3(0,6,0)
	await physics_frame
	await physics_frame
	weather.set_weather("rain",true)
	weather._process(0.3)
	assert(weather.sheltered and not weather.rain.visible)
	weather.resume_automatic()
	assert(not hud.has_meta("weather_override"))
	# Follow the generated schedule, then verify gradual rain cessation really stops audio.
	var plan = Weather.Schedule.day_plan(0,hud.game_clock.weather_seed)
	for entry in plan:
		hud.game_clock.elapsed_seconds = (entry.start+entry.end)*0.5
		weather._process(0.1)
		assert(weather.mode==entry.mode)
	weather.set_weather("storm",true)
	weather._process(0.1)
	weather.resume_automatic()
	hud.game_clock.elapsed_seconds = 1439
	weather._process(60.0)
	assert(weather.mode=="clear" and not weather.rain.emitting)
	assert(not weather.rain_audio.playing and not weather.rain_detail_audio.playing and not weather.rain_drizzle_audio.playing)
	print("PASS weather: schedule, cloud/light coupling, distinct drizzle/medium/storm mixes, three rain budgets, audio, delayed lightning/thunder, pause, clear cleanup, roof shelter")
	quit()
