extends SceneTree

## Offline eight-view atlas. Run with a real renderer; no baking during gameplay.
func _initialize() -> void:
	call_deferred("run")

func run() -> void:
	var viewport := SubViewport.new()
	viewport.size = Vector2i(512, 512)
	viewport.transparent_bg = true
	viewport.own_world_3d = true
	viewport.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	root.add_child(viewport)
	var world := Node3D.new()
	viewport.add_child(world)
	var environment := WorldEnvironment.new()
	var env := Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color.WHITE
	env.ambient_light_energy = 0.55
	environment.environment = env
	world.add_child(environment)
	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-40, -30, 0)
	sun.light_energy = 0.72
	world.add_child(sun)
	var camera := Camera3D.new()
	camera.projection = Camera3D.PROJECTION_ORTHOGONAL
	camera.size = 12.0
	world.add_child(camera)
	for variant in 6:
		var model := Node3D.new()
		world.add_child(model)
		for geometry in load("res://scenes/scenic_pine_geometry.gd").make_meshes(variant):
			var instance := MeshInstance3D.new()
			instance.mesh = geometry
			model.add_child(instance)
		var atlas := Image.create_empty(4096, 512, false, Image.FORMAT_RGBA8)
		for angle in 8:
			var yaw := angle * TAU / 8
			camera.position = Vector3(sin(yaw) * 25, 5, cos(yaw) * 25)
			camera.look_at(Vector3(0, 5, 0))
			for frame in 4:
				await process_frame
			await RenderingServer.frame_post_draw
			var image := viewport.get_texture().get_image()
			image.convert(Image.FORMAT_RGBA8)
			atlas.blit_rect(image, Rect2i(0, 0, 512, 512), Vector2i(angle * 512, 0))
		var result := atlas.save_png("res://assets/textures/scenic_valley/natural_pine_impostor_%d.png" % variant)
		print("[impostor-bake] variant=", variant, " result=", result)
		model.free()
	quit()
