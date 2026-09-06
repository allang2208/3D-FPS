extends SceneTree
func _initialize() -> void: call_deferred("run")
func run() -> void:
	var copper:=OS.get_environment("COPPER_PREVIEW")=="1"
	var precious:=OS.get_environment("PRECIOUS_PREVIEW")
	var viewport:=SubViewport.new()
	viewport.size=Vector2i(256,256)
	viewport.transparent_bg=true
	viewport.own_world_3d=true
	viewport.msaa_3d=Viewport.MSAA_4X
	viewport.render_target_update_mode=SubViewport.UPDATE_ALWAYS
	root.add_child(viewport)
	var world:=WorldEnvironment.new()
	world.environment=Environment.new()
	world.environment.ambient_light_source=Environment.AMBIENT_SOURCE_COLOR
	world.environment.ambient_light_color=Color.WHITE
	world.environment.ambient_light_energy=0.65
	viewport.add_child(world)
	var sun:=DirectionalLight3D.new()
	sun.rotation_degrees=Vector3(-50,-30,0)
	sun.light_energy=1.5
	viewport.add_child(sun)
	var model: Node3D=load("res://assets/models/polyhaven/boulder_01/boulder_01_2k.gltf").instantiate()
	viewport.add_child(model)
	var bounds: AABB=load("res://scenes/scenic_collision.gd").rock_geometry(model).bounds
	for child in model.find_children("","MeshInstance3D",true,false):
		child.material_override=load("res://scripts/tools/iron_vein_material.gd").create(child.mesh)
		if copper: child.material_override=load("res://scripts/tools/copper_vein_material.gd").create(child.mesh)
		if not precious.is_empty(): child.material_override=load("res://scripts/tools/precious_vein_material.gd").create(precious,child.mesh)
	var camera:=Camera3D.new()
	viewport.add_child(camera)
	var radius:=bounds.size.length()
	camera.position=bounds.get_center()+Vector3(1,0.8,1.3).normalized()*radius*2
	camera.look_at(bounds.get_center())
	camera.projection=Camera3D.PROJECTION_ORTHOGONAL
	camera.size=radius*1.03
	camera.near=0.001
	for i in 10: await process_frame
	await RenderingServer.frame_post_draw
	var kind:=precious if not precious.is_empty() else ("copper" if copper else "iron")
	viewport.get_texture().get_image().save_png("res://assets/environment/%s_vein_v1/%s_ore_icon.png" % [kind,kind])
	print("IRON_ICON PASS")
	quit()
