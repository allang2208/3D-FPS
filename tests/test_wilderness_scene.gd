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
	root.get_node("HUD")._ensure_built()
	var scene: Node3D=load("res://scenes/scenic_valley.tscn").instantiate()
	root.add_child(scene)
	current_scene=scene
	var editor: Node=scene.get_node("WildernessEditor")
	var building: Node=scene.get_node("BuildingSystem")
	var world: Node=editor.world
	var backpack: RefCounted=root.get_node("HUD").backpack
	assert(root.get_node("HUD").item_db.has_item("soil"))
	assert(building.allow_terrain_anchors and building.terrain_source==scene.terrain)
	assert(building.sidecar_suffix==".wilderness-building")
	editor.player.set_physics_process(false)
	editor.player.set_process_unhandled_input(false)
	Input.mouse_mode=Input.MOUSE_MODE_VISIBLE
	var pickaxe_key:=InputEventKey.new()
	pickaxe_key.keycode=KEY_7
	pickaxe_key.pressed=true
	editor._input(pickaxe_key)
	assert(editor.enabled and editor.toolkit.equipped=="pickaxe")
	assert(editor.gun.process_mode==Node.PROCESS_MODE_DISABLED and not editor.gun.visible)
	var camera: Camera3D=editor.camera
	camera.get_node("CameraFx").process_mode=Node.PROCESS_MODE_DISABLED
	camera.set_as_top_level(true)
	var center:=Vector3(-245,0,65)
	center.y=world.natural_height(center.x,center.z)
	camera.global_position=center+Vector3(0,5,0.2)
	camera.look_at(center)
	await physics_frame
	assert(not editor.target().is_empty())
	building.update_aim()
	assert(not building._aim.is_empty() and building._candidate.x>=building.minimum_cell.x and building._candidate.x<building.maximum_cell.x)
	var soil_before: int=backpack.count_item("soil")
	var fill_stock_before: int=world.stock[1]
	editor.toolkit.resolving=true # resolve_contact delegates to editor.act in gameplay
	assert(not editor.act(true))
	editor.toolkit.resolving=false
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
	editor.toolkit.resolving=true
	assert(editor.act(true))
	editor.toolkit.resolving=false
	assert(backpack.count_item("soil")==soil_before+1)
	assert(world.stock[1]==fill_stock_before)
	assert(FileAccess.file_exists(editor.save_path))
	# Find an unobstructed patch and prove the same building panel system can
	# establish a first structural block directly on Terrain3D.
	var build_cell:=Vector3i(999999,0,0)
	for wx in range(-252,-235):
		for wz in range(54,76):
			var candidate:=Vector3i(floori(wx/0.5),ceili((world.natural_height(wx,wz)-.001)/0.5),floori(wz/0.5))
			if building.placement_error(candidate,"wood",0).is_empty():
				build_cell=candidate
				break
		if build_cell.x!=999999: break
	assert(build_cell.x!=999999)
	assert(backpack.add_item("wood",1))
	var wood_before: int=backpack.count_item("wood")
	assert(building.place(build_cell,"wood",0).is_empty())
	assert(building.cells.get(build_cell)=="wood" and building.anchors.has(build_cell))
	assert(backpack.count_item("wood")==wood_before-1)
	assert(FileAccess.file_exists(building.save_path()))
	var foot:=Vector3(build_cell)*0.5
	var support_cell:=Vector3i(floori(foot.x),floori(world.natural_height(foot.x,foot.z)),floori(foot.z))
	assert(not building.terrain_excavation_error(support_cell).is_empty())
	assert(building.remove_block(build_cell).is_empty())
	assert(backpack.count_item("wood")==wood_before)
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
	print("WILDERNESS_SCENE PASS: terrain building, direct tool mode, backpack soil transaction, terrain ray excavation, distant region, soil layer, foliage refresh, save")
	scene.free()
	quit()
