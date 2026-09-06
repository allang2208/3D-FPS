extends SceneTree
const NAMES = ["rounded", "slab", "leaning", "ridge", "wedge", "saddle", "tall", "long"]
func _initialize() -> void: call_deferred("run")
func run() -> void:
	root.mode = Window.MODE_WINDOWED
	root.size = Vector2i(1920, 1000)
	var backdrop := ColorRect.new()
	backdrop.color = Color("17202b")
	backdrop.size = Vector2(1920, 1000)
	root.add_child(backdrop)
	var kinds := ["iron", "copper", "silver", "gold"]
	for row in 4:
		for col in 8:
			var panel := SubViewportContainer.new()
			panel.position = Vector2(col*240, row*250)
			root.add_child(panel)
			var viewport := SubViewport.new()
			viewport.size = Vector2i(240, 218)
			viewport.transparent_bg = true
			viewport.own_world_3d = true
			viewport.msaa_3d = Viewport.MSAA_4X
			panel.add_child(viewport)
			var world := WorldEnvironment.new()
			world.environment = Environment.new()
			world.environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
			world.environment.ambient_light_color = Color.WHITE
			world.environment.ambient_light_energy = 0.6
			viewport.add_child(world)
			var sun := DirectionalLight3D.new()
			sun.rotation_degrees = Vector3(-45, -35, 0)
			sun.light_energy = 1.7
			viewport.add_child(sun)
			var model: Node3D = load("res://assets/models/ore_variants/%s/model.scn" % NAMES[col]).instantiate()
			viewport.add_child(model)
			var bounds: AABB = load("res://scenes/scenic_collision.gd").rock_geometry(model).bounds
			for mi in model.find_children("", "MeshInstance3D", true, false):
				if row == 0: mi.material_override = load("res://scripts/tools/iron_vein_material.gd").create(mi.mesh)
				elif row == 1: mi.material_override = load("res://scripts/tools/copper_vein_material.gd").create(mi.mesh)
				else: mi.material_override = load("res://scripts/tools/precious_vein_material.gd").create(kinds[row], mi.mesh)
			var camera := Camera3D.new()
			viewport.add_child(camera)
			camera.position = bounds.get_center()+Vector3(1.0, 0.8, 1.6)*3
			camera.look_at(bounds.get_center())
			camera.projection = Camera3D.PROJECTION_ORTHOGONAL
			camera.size = maxf(bounds.size.length()*1.1, 1.05)
			camera.near = 0.01
			var label := Label.new()
			label.position = Vector2(col*240, row*250+218)
			label.size = Vector2(240, 32)
			label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
			label.text = kinds[row]+" / "+NAMES[col]
			label.add_theme_font_size_override("font_size", 16)
			root.add_child(label)
	for i in 20: await process_frame
	await RenderingServer.frame_post_draw
	root.get_texture().get_image().save_png("res://tools/basic-tools/ore-variants-preview.png")
	print("ORE_VARIANTS_PREVIEW PASS 32 combinations")
	quit()
