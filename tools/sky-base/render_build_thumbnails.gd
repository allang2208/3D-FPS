extends SceneTree

func _initialize() -> void:
	OS.set_environment("INVENTORY_SAVE_PATH", "user://build-thumbnails-%d.save" % OS.get_process_id())
	call_deferred("run")

func run() -> void:
	var viewport := SubViewport.new()
	viewport.size = Vector2i(256, 192)
	viewport.transparent_bg = true
	viewport.own_world_3d = true
	viewport.msaa_3d = Viewport.MSAA_4X
	viewport.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	root.add_child(viewport)
	var world := WorldEnvironment.new()
	world.environment = Environment.new()
	world.environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	world.environment.ambient_light_color = Color.WHITE
	world.environment.ambient_light_energy = 0.8
	viewport.add_child(world)
	var light := DirectionalLight3D.new()
	light.rotation_degrees = Vector3(-45, -30, 0)
	light.light_energy = 2.0
	viewport.add_child(light)
	var camera := Camera3D.new()
	viewport.add_child(camera)
	camera.position = Vector3(1, 1.025, 1.3)
	camera.look_at(Vector3(0, .225, 0))
	camera.projection = Camera3D.PROJECTION_ORTHOGONAL
	camera.size = 1.18
	var visual := MeshInstance3D.new()
	visual.mesh = preload("res://scripts/building/wood_block_mesh.gd").new().for_cell(Vector3i.ZERO, {Vector3i.ZERO: true})
	viewport.add_child(visual)
	var railing := preload("res://scripts/building/railing_component.gd").make_visual(
		preload("res://scripts/building/railing_material.gd").create_body(),
		preload("res://scripts/building/railing_material.gd").create_accent())
	viewport.add_child(railing)
	railing.hide()
	var door := preload("res://scripts/building/door_component.gd").make_preview(
		preload("res://scripts/building/railing_material.gd").create_body(),
		preload("res://scripts/building/generated_wood_material.gd").create(false),
		preload("res://scripts/building/railing_material.gd").create_accent())
	viewport.add_child(door)
	door.hide()
	DirAccess.make_dir_recursive_absolute("res://assets/ui/building")
	# The panel exposes material-stable blocks plus genuinely distinct components.
	# Legacy floor/wall/ceiling IDs remain load-only compatibility aliases and must
	# not regenerate retired purpose-specific thumbnails.
	var kinds := ["floor", "stone_floor", "marble", "railing", "door"]
	if not OS.get_environment("BUILD_THUMB_ONLY").is_empty(): kinds = [OS.get_environment("BUILD_THUMB_ONLY")]
	for kind in kinds:
		visual.visible = kind not in ["railing","door"]
		railing.visible = kind=="railing"
		door.visible = kind=="door"
		if kind=="door":
			camera.position=Vector3(2,1.8,2.6)
			camera.look_at(Vector3(.25,.75,0))
			camera.size=2.25
		else:
			camera.position=Vector3(1,1.025,1.3)
			camera.look_at(Vector3(0,.225,0))
			camera.size=1.18
		if kind not in ["railing","door"]:
			visual.material_override = preload("res://scripts/building/stone_material.gd").create() if kind.begins_with("stone_") else preload("res://scripts/building/generated_wood_material.gd").create(kind == "wall")
			if kind == "marble": visual.material_override = preload("res://scripts/building/marble_material.gd").create()
		for i in range(8): await process_frame
		await RenderingServer.frame_post_draw
		viewport.get_texture().get_image().save_png("res://assets/ui/building/%s.png" % kind)
	quit()
