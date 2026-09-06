extends SceneTree
const Lighting := preload("res://scripts/world_lighting.gd")
const Cycle := preload("res://scripts/day_night_environment.gd")
func _initialize() -> void:
	OS.set_environment("INVENTORY_SAVE_PATH","user://day-night-test-%d.save" % OS.get_process_id())
	call_deferred("run")
func run() -> void:
	var hud := root.get_node("HUD")
	hud._ensure_built()
	hud._save_queued = true
	var world := Node3D.new()
	root.add_child(world)
	current_scene = world
	var env = Lighting.create_environment()
	world.add_child(env)
	world.add_child(Lighting.create_sun())
	assert(env.environment.glow_enabled)
	assert(env.environment.glow_hdr_threshold > 0.7)
	await process_frame
	await process_frame
	env.weather.set_weather("clear",true)
	var sky_material := env.environment.sky.sky_material as ShaderMaterial
	env.apply_state(Cycle.sample(0.25))
	assert(is_equal_approx(sky_material.get_shader_parameter("sun_transmission"),1.0))
	env.weather.set_weather("storm",true)
	env.apply_state(Cycle.sample(0.25))
	assert(sky_material.get_shader_parameter("sun_transmission")<0.2)
	env.weather.set_weather("clear",true)
	for phase in [0.0,0.01,0.25,0.49,0.5,0.51,0.75,0.99,1.0]:
		var state := Cycle.sample(phase)
		env.apply_state(state)
		assert(not (env.sun.shadow_enabled and env.moon.shadow_enabled))
		assert(env.sun.basis.z.dot(state.direction) > 0.999)
		assert(env.moon.basis.z.dot(-state.direction) > 0.999)
		if state.direction.y < 0: assert(env.sun.light_energy == 0)
		if state.direction.y > 0: assert(env.moon.light_energy == 0)
	assert(Cycle.sample(0.0).direction.distance_to(Cycle.sample(1.0).direction)<0.0001)
	assert(Cycle.sample(0.25).direction.y>0.88)
	assert(Cycle.sample(0.75).direction.y< -0.88)
	hud.game_clock.elapsed_seconds = 0.0
	hud.game_clock.advance(60.0)
	assert(hud.game_clock.model().hour == 13)
	hud.game_clock.restore({"elapsedMs":360000.0})
	assert(hud.game_clock.model().hour == 0)
	assert(hud.game_clock.elapsed_seconds == hud.game_clock.DAY_SECONDS/2.0)
	hud.game_clock.elapsed_seconds = hud.game_clock.DAY_SECONDS/2.0
	var saved: Dictionary = hud.game_clock.serialize()
	hud.game_clock.advance(100)
	hud.game_clock.restore(saved)
	assert(hud.game_clock.model().hour == 0)
	paused = true
	var before: float = hud.game_clock.elapsed_seconds
	await process_frame
	await process_frame
	assert(hud.game_clock.elapsed_seconds == before)
	paused = false
	current_scene = null
	world.queue_free()
	await process_frame
	var next := Node3D.new()
	root.add_child(next)
	current_scene = next
	var next_env = Lighting.create_environment()
	next.add_child(next_env)
	next.add_child(Lighting.create_sun())
	await process_frame
	await process_frame
	assert(next_env.current_state.day < 0.01)
	next_env.weather.set_weather("clear",true)
	next_env.refresh()
	assert(next_env.moon.light_energy > 0.2)
	print("PASS day/night: orbit, HDR sun/moon glare, weather transmission, single shadow, phase wrap, restore, pause, scene transition")
	quit()
