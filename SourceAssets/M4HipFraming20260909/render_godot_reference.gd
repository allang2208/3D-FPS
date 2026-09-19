extends SceneTree
const Gun := preload("res://scripts/gun.gd")

func _initialize() -> void:
	render.call_deferred()

func render() -> void:
	var output := "D:/FPS3D/FPSGAME/SourceAssets/M4HipFraming20260909"
	var world := Node3D.new()
	root.add_child(world)
	current_scene = world
	var env := WorldEnvironment.new()
	env.environment = Environment.new()
	env.environment.background_mode = Environment.BG_COLOR
	env.environment.background_color = Color(0.12, 0.16, 0.19)
	env.environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.environment.ambient_light_color = Color.WHITE
	env.environment.ambient_light_energy = 0.5
	world.add_child(env)
	var body := CharacterBody3D.new()
	world.add_child(body)
	var camera := Camera3D.new()
	camera.fov = 75
	camera.near = 0.01
	camera.current = true
	body.add_child(camera)
	var light := DirectionalLight3D.new()
	light.rotation_degrees = Vector3(-35, -25, 0)
	light.light_energy = 1.1
	world.add_child(light)
	var report := {}
	for weapon in ["infima_ar"]:
		var gun := Gun.new()
		gun.data = load("res://weapon_data/" + weapon + ".tres")
		camera.add_child(gun)
		gun.set_process(false)
		gun.set_physics_process(false)
		for frame in 360:
			gun._physics_process(1.0 / 60.0)
			gun._process(1.0 / 60.0)
			if frame % 60 == 0: await process_frame
		await process_frame
		await RenderingServer.frame_post_draw
		root.get_texture().get_image().save_png(output.path_join("godot_" + weapon + "_hip.png"))
		var points := {}
		for socket in [&"RearSight", &"FrontSight", &"SOCKET_Muzzle"]:
			var pos: Vector3 = gun._model.socket_position(socket)
			points[str(socket)] = {"camera_local_m": str(camera.to_local(pos)), "screen_px": str(camera.unproject_position(pos))}
		report[weapon] = {"gun_position_m": str(gun.position), "gun_rotation": str(gun.rotation), "fov_vertical": camera.fov, "viewport": str(root.size), "sockets": points}
		gun.queue_free()
		await process_frame
	var file := FileAccess.open(output.path_join("godot_reference.json"), FileAccess.WRITE)
	file.store_string(JSON.stringify(report, "  "))
	file.close()
	print("GODOT_HIP_REFERENCE_PASS ", JSON.stringify(report))
	quit()
