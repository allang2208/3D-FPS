extends SceneTree
var lab: Node3D
var frames := 0
func _initialize() -> void:
	OS.set_environment("VOXEL_LAB_SAVE_PATH","user://hybrid-acceptance-"+str(OS.get_process_id())+".json")
	call_deferred("run")
func run() -> void:
	lab=load("res://scenes/voxel_valley_test.tscn").instantiate()
	root.add_child(lab)
	current_scene=lab
	lab.player.set_physics_process(false)
	lab.player.set_process_unhandled_input(false)
	lab.set_process_input(false)
	Input.mouse_mode=Input.MOUSE_MODE_VISIBLE
	lab.camera.set_as_top_level(true)
	lab.camera.global_position=lab.world.global_position+Vector3(-18,24,-18)
	lab.camera.look_at(lab.world.to_global(Vector3(0,lab.world.natural_height(0,0),0)))
	await physics_frame
	await physics_frame
	var misses := 0
	var max_error := 0.0
	for axis in 2:
		for side in [-1,1]:
			for along in [-12.3,-12.1,-11.9,-11.7,-10,-8,-6,-4,-2,0,2,4,6,8,10,11.7,11.9,12.1,12.3]:
				for offset in [-0.6,-0.2,0.2,0.6]:
					var local := Vector3(side*(24+offset),0,along*2) if axis==0 else Vector3(along*2,0,side*(24+offset))
					local.y=lab.world.natural_height(local.x,local.z)
					var p: Vector3=lab.world.to_global(local)
					var hit:=root.world_3d.direct_space_state.intersect_ray(PhysicsRayQueryParameters3D.create(p+Vector3.UP*20,p-Vector3.UP*20,1))
					if hit.is_empty():
						misses+=1
						if misses<6:
							print("GAP_SAMPLE axis=",axis," side=",side," offset=",offset," along=",along)
					else:
						max_error=maxf(max_error,absf(hit.position.y-p.y))
	print("HYBRID_BOUNDARY misses=",misses," max_height_error=",max_error)
	var p := Vector3i(0,floori(lab.world.natural_height(0,0))-2,0)
	var mined: bool=lab.world.mine(p)
	await physics_frame
	await physics_frame
	var center: Vector3=lab.world.to_global(Vector3(p)+Vector3.ONE*0.5)
	var hit:=root.world_3d.direct_space_state.intersect_ray(PhysicsRayQueryParameters3D.create(center+Vector3.UP*20,center-Vector3.UP*20,1))
	print("HYBRID_DIG changed=",mined," collider_is_voxel=",not hit.is_empty() and hit.collider.has_meta("voxel_chunk"))
	print("HYBRID_EDIT_SAMPLE ms=",lab.world.last_rebuild_ms," chunks=",lab.world.last_rebuilt_chunks)
	var protected_cell:=Vector3i(23,floori(lab.world.natural_height(23,0))-1,0)
	assert(not lab.world.mine(protected_cell))
	assert(not lab.world.can_place(Vector3i(23,14,0),1,AABB()))
	var saved_stock: Dictionary=lab.world.stock.duplicate()
	assert(lab.world.save_world(lab.save_path)==OK)
	assert(lab.world.undo_edit(AABB(Vector3(1000,1000,1000),Vector3.ONE)))
	assert(lab.world.get_cell(p)!=0)
	assert(lab.world.load_world(lab.save_path)==OK)
	assert(lab.world.get_cell(p)==0 and lab.world.stock==saved_stock)
	print("HYBRID_SAVE_RELOAD_AND_PROTECTED_EDGE PASS")
	var edit_times: Array[float]=[]
	for x in range(-6,6):
		var cell:=Vector3i(x,floori(lab.world.natural_height(x,3))-1,3)
		assert(lab.world.mine(cell))
		edit_times.append(lab.world.last_rebuild_ms)
	for i in 12:
		assert(lab.world.undo_edit(AABB(Vector3(1000,1000,1000),Vector3.ONE)))
	edit_times.sort()
	print("HYBRID_12_EDITS median_ms=",(edit_times[5]+edit_times[6])*0.5," max_ms=",edit_times.back())
	assert(misses==0 and max_error<0.3)
	assert(mined and not hit.is_empty() and hit.collider.has_meta("voxel_chunk"))
	print("HYBRID_ACCEPTANCE PASS")
func _process(_delta: float) -> bool:
	if lab==null:
		return false
	frames+=1
	if frames==250:
		if DisplayServer.get_name()!="headless":
			await RenderingServer.frame_post_draw
			print("HYBRID_CAPTURE ",root.get_texture().get_image().save_png("E:/无尽轮回/3d/voxel-valley-preview.png"))
		var records: Array=lab.control_pixels.duplicate()
		lab.free()
		var restored:=true
		for record in records:
			if record[0].get_pixelv(record[1]) != record[2]:
				restored=false
		print("HYBRID_RESTORE ",restored)
		assert(restored)
		quit()
	return false
