extends SceneTree
func _initialize() -> void:
	call_deferred("run")
func drain(world: Node) -> void:
	while not world.jobs.is_empty(): await process_frame
	await physics_frame
	await physics_frame
func run() -> void:
	var holder:=Node3D.new()
	root.add_child(holder)
	var camera:=Camera3D.new()
	holder.add_child(camera)
	var terrain:=Terrain3D.new()
	holder.add_child(terrain)
	terrain.region_size=256
	var heights:=Image.create_empty(512,512,false,Image.FORMAT_RF)
	heights.fill(Color(5,0,0,1))
	terrain.data.import_images([heights,null,null],Vector3(-256,0,-256),0.0,1.0)
	terrain.collision.set_mode(Terrain3DCollision.FULL_GAME)
	terrain.collision.build()
	var world:=preload("res://scripts/voxel_lab/wilderness_world.gd").new()
	world.terrain=terrain
	holder.add_child(world)
	assert(world.chunks.is_empty())
	var cell:=Vector3i(-85,4,34)
	world.prepare_at(cell)
	assert(not world.ready_at(cell))
	await drain(world)
	assert(world.ready_at(cell))
	var gaps:=0
	for x in [-97.1,-97.0,-96.9,-96.5,-90,-80,-72.5,-72.1,-72.0,-71.9]:
		for z in [22.9,23.0,23.1,23.5,30,40,47.5,47.9,48.0,48.1]:
			var hit:=root.world_3d.direct_space_state.intersect_ray(PhysicsRayQueryParameters3D.create(Vector3(x,15,z),Vector3(x,-5,z),1))
			if hit.is_empty() or absf(hit.position.y-5)>0.02:
				gaps+=1
				print("WILDERNESS_GAP ",x," ",z)
	assert(gaps==0)
	assert(world.mine(cell))
	assert(world.density(Vector3(cell)+Vector3.ONE*0.5)>0)
	assert(world.surface_weights(Vector3(cell)+Vector3(0.5,0.2,0.5)).g>0.99)
	var seam:=Vector3i(-80,4,34)
	world.prepare_at(seam)
	await drain(world)
	assert(world.mine(seam))
	var far:=Vector3i(90,4,-90)
	world.prepare_at(far)
	await drain(world)
	assert(world.mine(far))
	assert(world.density(Vector3(cell)+Vector3.ONE*0.5)>0)
	var save: String="user://wilderness-fixture-"+str(OS.get_process_id())+".json"
	assert(world.save_world(save)==OK)
	assert(world.undo_edit(AABB(Vector3(500,500,500),Vector3.ONE)))
	assert(world.load_world(save)==OK)
	await drain(world)
	assert(world.edits.size()==3 and world.get_cell(far)==0)
	assert(world.surface_weights(Vector3(-82,4.7,34)).g>0.99)
	assert(world.place(cell,1,AABB(Vector3(500,500,500),Vector3.ONE)))
	assert(not world.edits.has(cell))
	assert(world.surface_weights(Vector3(cell)+Vector3(0.5,1.0,0.5)).g>0.99)
	assert(world.save_world(save)==OK)
	var records: Array=world.source_pixels.values()
	world.free()
	for record in records: assert(record[0].get_pixelv(record[1])==record[2])
	var restored:=preload("res://scripts/voxel_lab/wilderness_world.gd").new()
	restored.terrain=terrain
	holder.add_child(restored)
	assert(restored.load_world(save)==OK)
	await drain(restored)
	assert(restored.edits.size()==2 and restored.soil_scars.has(Vector2i(cell.x,cell.z)))
	assert(restored.surface_weights(Vector3(cell)+Vector3(0.5,1.0,0.5)).g>0.99)
	assert(restored.mine(Vector3i(-84,4,34)))
	restored.exit_save_path=save+".exit"
	restored.free()
	assert(JSON.parse_string(FileAccess.get_file_as_string(save+".exit")).edits.size()==3)
	print("WILDERNESS_ACCEPTANCE PASS: lazy allocation, 100 seam rays, cross-column and distant edits, brown subsoil, undo/save/reload, source restoration")
	holder.free()
	quit()
