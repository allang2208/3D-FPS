extends SceneTree
const OUT := "res://tools/ai-gen/foreman-motion-v04-20260906/runtime"
func _initialize() -> void:
	OS.set_environment("INVENTORY_SAVE_PATH","user://foreman-preview-isolated.save")
	root.size=Vector2i(960,720)
	call_deferred("run_render")
func snap(path: String) -> void:
	await process_frame
	await RenderingServer.frame_post_draw
	root.get_texture().get_image().save_png(OUT.path_join(path+".png"))
func run_render() -> void:
	DirAccess.make_dir_recursive_absolute(OUT)
	var world=load("res://scenes/foreman_demo.tscn").instantiate()
	root.add_child(world)
	current_scene=world
	await process_frame
	var enemy=world.get_node("ForemanZombie")
	if not OS.get_cmdline_user_args().has("--formal"):
		var old_transform=enemy.transform
		enemy.free()
		enemy=load("res://scenes/enemies/foreman_zombie.tscn").instantiate()
		enemy.get_node("Model").free()
		var model=load("res://tools/ai-gen/foreman-motion-v04-20260906/foreman-motion-v04.glb").instantiate()
		model.name="Model"
		enemy.add_child(model)
		enemy.transform=old_transform
		world.add_child(enemy)
	var player=world.get_node("Player")
	player.hp=10000
	player.set_physics_process(false)
	await snap("gameplay")
	enemy.set_physics_process(false)
	for cave in get_nodes_in_group("foreman_mine_caves"):
		cave.set_physics_process(false)
		cave.hide()
	player.hide()
	for node in root.get_children():
		if node is CanvasLayer:node.hide()
	for node in world.get_children():
		if node is CanvasLayer:node.hide()
	var camera:=Camera3D.new()
	world.add_child(camera)
	camera.position=Vector3(-4,3.2,7)
	camera.look_at(Vector3(0,1.18,.35))
	camera.projection=Camera3D.PROJECTION_ORTHOGONAL
	camera.size=5.0
	camera.current=true
	for clip in ["Idle","Walk","Attack","Death","WalkGameSpeed"]:
		if OS.get_cmdline_user_args().has("--speed-only") and clip!="WalkGameSpeed":continue
		if OS.get_cmdline_user_args().has("--attack-only") and clip!="Attack":continue
		DirAccess.make_dir_recursive_absolute(OUT.path_join(clip))
		var source_clip="Walk" if clip=="WalkGameSpeed" else clip
		var rate=enemy.chase_speed/enemy.walk_reference_speed if clip=="WalkGameSpeed" else 1.0
		var duration: float=enemy._ap.get_animation(source_clip).length/rate
		for i in range(0 if OS.get_cmdline_user_args().has("--key-only") else ceili(duration*24)+1):
			enemy._sync_pose(source_clip,minf(i/24.0,duration)*rate)
			await snap("%s/%03d" % [clip,i])
		enemy._sync_pose(source_clip,(.59625 if clip=="Attack" else duration*.5 if clip!="Death" else duration)*rate)
		await snap(clip+"-key")
		if clip=="Attack" or clip=="Death":
			var old_position=camera.position
			for view in ["front","side"]:
				camera.position=Vector3(0,2,6) if view=="front" else Vector3(-6,2,0)
				camera.look_at(Vector3(0,1.15,0))
				await snap(clip+"-"+view)
			camera.position=old_position
			camera.look_at(Vector3(0,1.18,.35))
	print("FOREMAN_RENDER %s sampled on default renderer" % ("Attack" if OS.get_cmdline_user_args().has("--attack-only") else "four exported clips plus game-speed Walk"))
	world.queue_free()
	await process_frame
	quit()
