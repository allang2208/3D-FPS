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
	for level in 6:
		var model := Node3D.new()
		world.add_child(model)
		var triangles := 0
		for geometry in load("res://scenes/scenic_pine_geometry.gd").make_meshes(level):
			var instance := MeshInstance3D.new()
			instance.mesh = geometry
			model.add_child(instance)
			triangles += geometry.surface_get_array_len(0) / 3
			var box: AABB = geometry.get_aabb()
			assert(box.position.y >= -0.001 and box.end.y < 11)
			assert(maxf(absf(box.position.x), absf(box.end.x)) < 5.8)
			assert(maxf(absf(box.position.z), absf(box.end.z)) < 5.8)
		print("[pine] variant=", level, " triangles=", triangles)
		assert(triangles < 6500)
		model.position.x = (level - 2.5) * 7
		for mesh in model.get_children():
			mesh.visibility_range_begin = 0
			mesh.visibility_range_end = 0
			mesh.visible = true
		var label := Label3D.new()
		label.text = "Pine %d" % (level + 1)
		label.position = Vector3((level - 2.5) * 7, -1, 0)
		label.font_size = 40
		label.pixel_size = 0.008
		world.add_child(label)
	var camera := Camera3D.new()
	world.add_child(camera)
	camera.position = Vector3(0, 5, 35)
	camera.projection = Camera3D.PROJECTION_ORTHOGONAL
	camera.size = 18
	for frame in 20:
		await process_frame
	await RenderingServer.frame_post_draw
	root.get_texture().get_image().save_png("res://docs/preview/valley_pine_variants.png")
	quit()
