extends SceneTree
func _initialize() -> void:
	OS.set_environment("WILDERNESS_SAVE_PATH","user://wilderness-scene-"+str(OS.get_process_id())+".json")
	OS.set_environment("INVENTORY_SAVE_PATH","user://wilderness-inventory-"+str(OS.get_process_id())+".save")
	call_deferred("run")
func drain(world: Node) -> void:
	while not world.jobs.is_empty(): await process_frame
	await physics_frame
	await physics_frame
func run() -> void:
	var scene: Node3D=load("res://scenes/scenic_valley.tscn").instantiate()
	root.add_child(scene)
	current_scene=scene
	var editor: Node=scene.get_node("WildernessEditor")
	var world: Node=editor.world
	editor.player.set_physics_process(false)
	editor.player.set_process_unhandled_input(false)
	Input.mouse_mode=Input.MOUSE_MODE_VISIBLE
	editor.set_enabled(true)
	assert(editor.gun.process_mode==Node.PROCESS_MODE_DISABLED and not editor.gun.visible)
	var camera: Camera3D=editor.camera
	if camera.has_node("CameraFx"): camera.get_node("CameraFx").process_mode=Node.PROCESS_MODE_DISABLED
	camera.set_as_top_level(true)
	var center:=Vector3(-245,0,65)
	center.y=world.natural_height(center.x,center.z)
	camera.global_position=center+Vector3(0,5,0.2)
	camera.look_at(center)
	await physics_frame
	assert(not editor.target().is_empty())
	assert(not editor.act(true))
	await drain(world)
	var gaps:=0
	for xi in 53:
		for zi in 53:
			var point:=Vector3(-257.1+xi*0.5,100,55-0.1+zi*0.5)
			var hit:=root.world_3d.direct_space_state.intersect_ray(PhysicsRayQueryParameters3D.create(point,point-Vector3.UP*165,1))
			if hit.is_empty():
				gaps+=1
				if gaps<5: print("WILDERNESS_SLOPE_GAP ",point)
	print("WILDERNESS_SLOPE_RAYS gaps=",gaps)
	assert(gaps==0)
	assert(editor.act(true))
	for z in range(63,68):
		for x in range(-247,-242):
			var height: int=floori(world.natural_height(x+0.5,z+0.5))
			for y in range(height-2,height+1):
				var p:=Vector3i(x,y,z)
				if world.get_cell(p)!=0: world.mine(p)
	var far:=Vector3i(-60,floori(world.natural_height(-60,-50)),-50)
	world.prepare_at(far)
	await drain(world)
	if world.get_cell(far)==0: far.y-=1
	assert(world.mine(far))
	editor._refresh_foliage()
	editor._save()
	assert(FileAccess.file_exists(editor.save_path))
	assert(world.surface_weights(center-Vector3.UP*0.4).g==1.0)
	camera.global_position=center+Vector3(-10,10,-11)
	camera.look_at(center-Vector3.UP)
	Input.mouse_mode=Input.MOUSE_MODE_VISIBLE
	for i in 120: await process_frame
	if DisplayServer.get_name()!="headless":
		await RenderingServer.frame_post_draw
		root.get_texture().get_image().save_png("E:/无尽轮回/3d/wilderness-soil-preview.png")
	editor.set_enabled(false)
	assert(editor.gun.process_mode!=Node.PROCESS_MODE_DISABLED and editor.gun.visible)
	print("WILDERNESS_SCENE PASS: real valley, weapon toggle, terrain ray input, excavation, distant region, soil layer, foliage refresh, save")
	scene.free()
	quit()
