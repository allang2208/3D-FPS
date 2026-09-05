extends SceneTree

func _initialize() -> void:
	call_deferred("run")

func run() -> void:
	var world := Node3D.new()
	root.add_child(world)
	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-40, -30, 0)
	sun.light_energy = 0.72
	world.add_child(sun)
	var environment := WorldEnvironment.new()
	var env := Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color(0.4, 0.48, 0.52)
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color.WHITE
	env.ambient_light_energy = 0.55
	environment.environment = env
	world.add_child(environment)
	for level in 3:
		var model: Node3D = load("res://scenes/scenic_conifer.tscn").instantiate()
		world.add_child(model)
		model.setup_lod()
		model.position.x = (level - 1) * 10
		for mesh in model.get_children():
			mesh.visibility_range_begin = 0
			mesh.visibility_range_end = 0
			mesh.visible = mesh.get_meta("scenic_lod") == level
		var label := Label3D.new()
		label.text = ["Near: 5810 tris", "Mid: 2352 tris", "Far: 2 tris / 8 views"][level]
		label.position = Vector3((level - 1) * 10, -1, 0)
		label.font_size = 40
		label.pixel_size = 0.008
		world.add_child(label)
	var camera := Camera3D.new()
	world.add_child(camera)
	camera.position = Vector3(0, 5, 35)
	camera.projection = Camera3D.PROJECTION_ORTHOGONAL
	camera.size = 19
	for frame in 20:
		await process_frame
	await RenderingServer.frame_post_draw
	root.get_texture().get_image().save_png("res://docs/preview/valley_lod_comparison.png")
	quit()
