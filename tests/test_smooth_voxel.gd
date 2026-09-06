extends SceneTree
const World := preload("res://scripts/voxel_lab/smooth_world.gd")
var failures := 0
func _initialize() -> void:
	call_deferred("run")
func check(ok: bool, label: String) -> void:
	print("PASS " if ok else "FAIL ",label)
	if not ok:
		failures += 1
func signatures(world: Node3D) -> Dictionary:
	var result := {}
	for key in world.chunks:
		var mesh: ArrayMesh = world.chunks[key].get_node("Mesh").mesh
		var values := []
		if mesh != null:
			for surface in mesh.get_surface_count():
				var arrays := mesh.surface_get_arrays(surface)
				values.append(hash(arrays[Mesh.ARRAY_VERTEX]))
				values.append(hash(arrays[Mesh.ARRAY_NORMAL]))
		result[key] = values
	return result
func run() -> void:
	root.get_node("HUD").set_process(false)
	var world := World.new()
	root.add_child(world)
	await physics_frame
	await physics_frame
	check(absf(world.natural_height(0.2,0.3)-roundf(world.natural_height(0.2,0.3))) > 0.001,"continuous non-integer surface heights")
	check(world.mine(Vector3i(0,0,0)),"excavation at three-chunk-axis junction")
	var incremental := signatures(world)
	world.rebuild_all()
	check(incremental == signatures(world),"incremental edit equals full rebuild across chunk junction")
	var vertices_seen := {}
	var shared := 0
	var mismatch := 0
	for chunk in world.chunks:
		var mesh: ArrayMesh = world.chunks[chunk].get_node("Mesh").mesh
		if mesh == null:
			continue
		var arrays := mesh.surface_get_arrays(0)
		for i in arrays[Mesh.ARRAY_VERTEX].size():
			var p: Vector3 = arrays[Mesh.ARRAY_VERTEX][i]
			var n: Vector3 = arrays[Mesh.ARRAY_NORMAL][i]
			var key := p.snapped(Vector3.ONE*0.00001)
			if vertices_seen.has(key) and vertices_seen[key][0] != chunk:
				shared += 1
				if n.distance_to(vertices_seen[key][1]) > 0.0001:
					mismatch += 1
			else:
				vertices_seen[key] = [chunk,n]
	check(shared > 100 and mismatch == 0,"shared boundary vertices have identical smooth normals")
	var cave := Vector3i(7,3,0)
	var old_stock := world.stock.duplicate()
	var kind := world.get_cell(cave)
	check(world.mine(cave),"mine into solid mountain")
	check(world.density(Vector3(cave)+Vector3.ONE*0.5)>0 and world.density(Vector3(cave)+Vector3(0.5,2.5,0.5))<0,"rounded empty cavity preserves solid roof")
	await physics_frame
	await physics_frame
	var hit := world.get_world_3d().direct_space_state.intersect_ray(PhysicsRayQueryParameters3D.create(Vector3(7.5,3.5,0.5),Vector3(7.5,6,0.5),1))
	check(not hit.is_empty() and hit.position.y>3.5,"smooth cavity has physical ceiling")
	check(world.stock[kind] == old_stock[kind]+1,"smooth excavation awards material once")
	check(world.place(cave,kind,AABB(Vector3(100,100,100),Vector3.ONE)),"refill smooth cavity")
	check(world.density(Vector3(cave)+Vector3.ONE*0.5)<0 and world.stock==old_stock,"refill restores volume and material count")
	var undo_mesh := signatures(world)
	world.mine(cave)
	check(not world.undo_edit(AABB(Vector3(cave),Vector3.ONE)),"undo cannot restore rock around player")
	check(world.undo_edit(AABB(Vector3(100,100,100),Vector3.ONE)) and world.stock==old_stock and signatures(world)==undo_mesh,"undo restores terrain and material count exactly")
	world.mine(cave)
	world.place(cave,4,AABB(Vector3(100,100,100),Vector3.ONE))
	check(world.density(Vector3(cave)+Vector3(0.5,-0.15,0.5))<0,"brick replacement preserves soil directly below footprint")
	world.undo_edit(AABB(Vector3(100,100,100),Vector3.ONE))
	world.undo_edit(AABB(Vector3(100,100,100),Vector3.ONE))
	var p := Vector3i(-12,world.height_at(-12,10),10)
	check(not world.can_place(p,1,AABB(Vector3(p)+Vector3(1.1,0.1,0.1),Vector3(0.5,1.8,0.6))),"rounded fill rejects player overlap beyond voxel cell")
	check(world.place(p,4,AABB(Vector3(100,100,100),Vector3.ONE)),"brick construction stays a separate cubic surface")
	var path := "user://smooth-test-"+str(OS.get_process_id())+".json"
	check(world.save_world(path)==OK,"save smooth generator format")
	var before := signatures(world)
	world.reset_data()
	check(world.load_world(path)==OK and signatures(world)==before,"reload restores exact mesh and edits")
	check(world.edit_history.is_empty(),"loading resets session undo history")
	DirAccess.remove_absolute(ProjectSettings.globalize_path(path))
	print("SMOOTH_GEOMETRY shared_vertices=",shared," mismatched_normals=",mismatch," triangles=",world.triangle_count," last_edit_ms=",world.last_rebuild_ms)
	world.queue_free()
	await process_frame
	print("SMOOTH_ACCEPTANCE failures=",failures)
	quit(0 if failures==0 else 1)
