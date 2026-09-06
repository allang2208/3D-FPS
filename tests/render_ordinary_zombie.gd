extends SceneTree
## Render actual main-scene import with Godot; exits after four PNGs.
const OUT := "E:/无尽轮回/3d/3-dfps/tools/ai-gen/zombie-3d-v01-20260905/runtime-tests"
func _initialize() -> void:
	call_deferred("_run")
func _run() -> void:
	var main: Node3D = load("res://scenes/main.tscn").instantiate()
	root.add_child(main)
	current_scene = main
	await process_frame
	var z: Node3D = main.get_node_or_null("OrdinaryZombie")
	if z == null:
		push_error("Main scene did not spawn OrdinaryZombie")
		quit(1)
		return
	main.get_node("Player").set_physics_process(false)
	var wolf := main.get_node_or_null("WolfEnemy")
	if wolf:
		wolf.set_physics_process(false)
	# Exercise real physics in the shipped room before capturing fixed poses.
	z.process_mode = Node.PROCESS_MODE_ALWAYS
	var start := z.global_position
	for i in 120:
		await physics_frame
	var distance := Vector2(z.global_position.x - start.x, z.global_position.z - start.z).length()
	if distance < 0.8 or z._clip != "Walk" or absf(z.global_position.y - start.y) > 0.15:
		push_error("Main-scene chase failed: distance=" + str(distance) + " clip=" + z._clip)
		quit(1)
		return
	print("ZOMBIE_MAIN_CHASE PASS distance=", distance, " clip=", z._clip)
	z.process_mode = Node.PROCESS_MODE_DISABLED
	var cam := Camera3D.new()
	root.add_child(cam)
	cam.fov = 48
	cam.current = true
	DirAccess.make_dir_recursive_absolute(OUT)
	for entry in [["Idle", 0.0], ["Walk", .6], ["Attack", .375], ["Death", 2.0]]:
		var clip: String = entry[0]
		z._sync_pose(clip, entry[1])
		var center := z.global_position + Vector3(0, .9, 0)
		cam.position = z.global_position + Vector3(-2.5, 1.7, 3.3)
		if clip == "Death":
			center += Vector3(0, -.5, -.3)
		cam.look_at(center)
		for i in 4:
			await process_frame
		await RenderingServer.frame_post_draw
		var path := OUT.path_join(clip.to_lower()+"-godot.png")
		var error := root.get_texture().get_image().save_png(path)
		if error != OK:
			push_error("Failed screenshot " + path)
			quit(1)
			return
		print("ZOMBIE_RENDER ", clip, " ", path)
	quit(0)
