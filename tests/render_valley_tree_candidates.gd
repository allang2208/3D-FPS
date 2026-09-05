extends SceneTree

func _initialize() -> void:
	call_deferred("run")

func run() -> void:
	var world := Node3D.new()
	root.add_child(world)
	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-40, -30, 0)
	sun.shadow_enabled = true
	world.add_child(sun)
	var environment := WorldEnvironment.new()
	var env := Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color(0.42, 0.49, 0.54)
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color.WHITE
	env.ambient_light_energy = 0.4
	environment.environment = env
	world.add_child(environment)
	var assets := ["island_tree_01/island_tree_01_1k", "island_tree_02/island_tree_02_1k", "tree_small_02/tree_small_02_1k", "pine_sapling_small/pine_sapling_small_1k"]
	var helper = load("res://scenes/scenic_collision.gd")
	for i in assets.size():
		var model: Node3D = load("res://scenes/scenic_conifer.tscn" if i == 0 else "res://assets/models/polyhaven/" + assets[i] + ".gltf").instantiate()
		world.add_child(model)
		if "pine_sapling" in assets[i]:
			var selected: Node3D = model.get_child(0)
			for child in model.get_children():
				if child != selected:
					child.free()
			selected.position = Vector3.ZERO
		var box: AABB = helper.bounds(helper.mesh_points(model))
		var factor := 5.0 / box.size.y
		model.scale = Vector3.ONE * factor
		model.position = Vector3(i * 7.0 - 10.5, -box.position.y * factor, 0)
		for mesh in model.find_children("", "MeshInstance3D", true, false):
			for surface in mesh.mesh.get_surface_count():
				var mat: Material = mesh.get_active_material(surface)
				print("[candidate] ", assets[i], " ", mat.resource_name)
		var label := Label3D.new()
		label.text = "scenic_conifer" if i == 0 else assets[i].get_slice("/", 0)
		label.position = Vector3(i * 7 - 10.5, -0.7, 0)
		label.font_size = 44
		label.pixel_size = 0.007
		world.add_child(label)
	var camera := Camera3D.new()
	world.add_child(camera)
	camera.position = Vector3(0, 5, 24)
	camera.look_at(Vector3(0, 2.5, 0))
	camera.projection = Camera3D.PROJECTION_ORTHOGONAL
	camera.size = 16
	for i in 15:
		await process_frame
	await RenderingServer.frame_post_draw
	root.get_texture().get_image().save_png("res://docs/preview/valley_tree_candidates.png")
	quit()
