extends SceneTree
func _initialize() -> void:
	OS.set_environment("WILDERNESS_SAVE_PATH","user://scenic-rock-test-"+str(OS.get_process_id())+".json")
	OS.set_environment("INVENTORY_SAVE_PATH","user://scenic-rock-inventory-"+str(OS.get_process_id())+".save")
	call_deferred("run")

func run() -> void:
	var iron:=OS.get_environment("IRON_HARVEST_TEST")=="1"
	var copper:=OS.get_environment("COPPER_HARVEST_TEST")=="1"
	if copper: iron=true
	var item: String="iron_ore" if iron else "stone"
	if copper: item="copper_ore"
	var precious:=OS.get_environment("PRECIOUS_HARVEST_TEST")
	if not precious.is_empty():
		iron=true
		item=precious+"_ore"
	root.get_node("HUD")._ensure_built()
	var scene: Node3D=load("res://scenes/scenic_valley.tscn").instantiate()
	root.add_child(scene)
	current_scene=scene
	var editor: Node=scene.get_node("WildernessEditor")
	editor.set_physics_process(false)
	editor.player.set_physics_process(false)
	var kit: Node=editor.toolkit
	kit.set_process(false)
	editor.set_enabled(true)
	var rock: Node3D
	for body in scene.get_children():
		if body.has_meta("rock_source") and body.get_meta("rock_extent")<2.0 and body.get_meta("harvest_item","stone")==item:
			rock=body
			break
	assert(rock!=null)
	if iron:
		assert(rock.has_meta("harvest_identity") and rock.has_meta("rock_fragments"))
		assert(rock.get_meta("rock_fragments") is Resource)
		assert("/polyhaven/" in kit.rocks.rock_id(rock))
		var shapes: Dictionary = {}
		for body in scene.get_children():
			if body.has_meta("rock_fragments"):
				shapes[body.get_meta("rock_source")] = true
				var bounds: AABB = body.get_meta("local_bounds")
				bounds.position += body.position
				assert(bounds.end.y - scene.terrain.data.get_height(bounds.get_center()) >= bounds.size.y * 0.25)
		assert(shapes.size() >= 6)
		print("ORE variety in valley=", shapes.size(), " legacy identity=", kit.rocks.rock_id(rock))
	var batch: MultiMeshInstance3D
	for node in scene.get_children():
		if node is MultiMeshInstance3D and node.get_meta("harvest_batch_key","")==rock.get_meta("harvest_batch_key"):
			batch=node
			break
	assert(batch!=null)
	var index: int=rock.get_meta("harvest_index")
	var original:=batch.multimesh.get_instance_transform(index)
	if iron:
		var ore_box: AABB = original * batch.multimesh.mesh.get_aabb()
		var ground: float = scene.terrain.data.get_height(ore_box.get_center())
		print("ORE bounds=", ore_box, " ground=", ground, " source=", rock.get_meta("rock_source"))
		assert(ore_box.end.y - ground >= ore_box.size.y * 0.25)
	var other: Array=[]
	for i in batch.multimesh.instance_count: other.append(batch.multimesh.get_instance_transform(i))
	var before: int=editor.world.stock[2]
	var bp: RefCounted=root.get_node("HUD").backpack
	var inventory_before: int=bp.count_item(item)
	print("HARVEST target=",item," position=",rock.global_position)
	if iron and DisplayServer.get_name()!="headless":
		var cam: Camera3D=editor.camera
		cam.set_as_top_level(true)
		cam.get_node("CameraFx").process_mode=Node.PROCESS_MODE_DISABLED
		var box: AABB=original*batch.multimesh.mesh.get_aabb()
		cam.global_position=box.get_center()+Vector3(1.6,1.4,2.1)*maxf(box.size.x,box.size.z)
		cam.look_at(box.get_center())
		root.size=Vector2i(1280,720)
		for i in 12: await process_frame
		await RenderingServer.frame_post_draw
		root.get_texture().get_image().save_png("res://tools/basic-tools/"+item+"-in-world.png")
	var at:=rock.global_position+Vector3.UP*0.5
	kit.equip("axe")
	assert(not kit.rocks.strike(rock,at,Vector3.UP))
	kit.equip("pickaxe")
	assert(kit.rocks.strike(rock,at,Vector3.UP))
	assert(kit.rocks.strike(rock,at,Vector3.UP))
	assert(editor.world.stock[2]==before)
	assert(batch.multimesh.get_instance_transform(index)==original)
	var started:=Time.get_ticks_msec()
	assert(kit.rocks.strike(rock,at,Vector3.UP))
	print("ROCK fracture ms=",Time.get_ticks_msec()-started)
	assert(editor.world.stock[2]==before+(0 if iron else 1))
	assert(bp.count_item(item)==inventory_before+1)
	assert(not kit.rocks.strike(rock,at,Vector3.UP))
	assert(kit.rocks.last_effect.pieces.size()==8)
	for piece in kit.rocks.last_effect.pieces:
		var mesh: Mesh=piece.get_child(0).mesh
		if iron:
			assert(mesh.surface_get_material(0).shader==batch.multimesh.mesh.surface_get_material(0).shader)
		else: assert(mesh.surface_get_material(0)==batch.multimesh.mesh.surface_get_material(0))
		assert(piece.collision_layer==0 and piece.collision_mask==1)
	for i in batch.multimesh.instance_count:
		if i!=index: assert(batch.multimesh.get_instance_transform(i)==other[i])
	assert(editor.world.load_world(editor.save_path)==OK)
	editor._refresh_foliage()
	assert(batch.multimesh.get_instance_transform(index).origin.y== -10000)
	assert(editor.world.stock[2]==before+(0 if iron else 1))
	await physics_frame
	await physics_frame
	assert(rock.get_child(0).disabled)
	print("SCENIC_ROCK PASS: real batch model, 3 hits, 8 source-mesh fragments, same material, one reward, neighbor preserved, save/load and foliage refresh")
	# Let SceneTree tear down together; HUD timeline still holds the scene until exit.
	quit()
