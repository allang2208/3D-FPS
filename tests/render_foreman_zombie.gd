extends SceneTree
const OUT := "res://tools/ai-gen/foreman-v01-20260906/runtime"
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
	if OS.get_cmdline_user_args().has("--whip-candidate") or OS.get_cmdline_user_args().has("--arm-candidate"):
		var old_transform=enemy.transform
		enemy.free()
		enemy=load("res://scenes/enemies/foreman_zombie.tscn").instantiate()
		enemy.get_node("Model").free()
		var candidate="foreman-arm-v03.glb" if OS.get_cmdline_user_args().has("--arm-candidate") else "foreman-whip-v02.glb"
		var model=load("res://tools/ai-gen/foreman-v01-20260906/"+candidate).instantiate()
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
	camera.look_at(Vector3(0,1.2,1.0))
	camera.projection=Camera3D.PROJECTION_ORTHOGONAL
	camera.size=6.5
	camera.current=true
	for clip in ["Idle","Walk","Attack","Howl","Death"]:
		if OS.get_cmdline_user_args().has("--attack-only") and clip!="Attack":continue
		DirAccess.make_dir_recursive_absolute(OUT.path_join(clip))
		var duration: float=enemy._ap.get_animation(clip).length
		for i in range(0 if OS.get_cmdline_user_args().has("--key-only") else ceili(duration*24)+1):
			enemy._sync_pose(clip,minf(i/24.0,duration))
			await snap("%s/%03d" % [clip,i])
		enemy._sync_pose(clip,.59625 if clip=="Attack" else duration*.5 if clip!="Death" else duration)
		await snap(clip+"-key")
	print("FOREMAN_RENDER %s sampled on default renderer" % ("Attack" if OS.get_cmdline_user_args().has("--attack-only") else "five exported clips"))
	world.queue_free()
	await process_frame
	quit()
