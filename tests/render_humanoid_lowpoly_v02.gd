extends SceneTree
var OUT := ProjectSettings.globalize_path("res://tools/ai-gen/humanoid-detail-v02-20260906/runtime")
func _initialize() -> void:
	call_deferred("run_review")
func run_review() -> void:
	var main = load("res://scenes/main.tscn").instantiate()
	root.add_child(main)
	current_scene = main
	root.get_node("HUD").ensure_for_current_scene()
	await process_frame
	var actors: Array = [main.get_node("OrdinaryZombie"), main.get_node("MinerWorkwearZombie"), main.get_node("RunnerZombie")]
	for child in main.get_children():
		if child is CharacterBody3D:
			child.set_physics_process(false)
			if child not in actors: child.hide()
	for i in actors.size():
		var actor: Node3D = actors[i]
		assert(actor._player == main.get_node("Player"))
		assert(actor._model.scene_file_path.ends_with("_v02.glb"))
		actor.position = Vector3(-7.5+i*2.2, 0, -4)
		actor.rotation.y = 0
	var cam := Camera3D.new()
	main.add_child(cam)
	cam.current = true
	cam.fov = 44
	cam.global_position = Vector3(-6.7, 2.7, 4.7)
	cam.look_at(Vector3(-5.3, .9, -4))
	DirAccess.make_dir_recursive_absolute(OUT)
	for entry in [["Idle", .4], ["Walk", .6], ["Attack", .65], ["Death", 2.4]]:
		for actor in actors: actor._sync_pose(entry[0], entry[1])
		for i in 4: await process_frame
		if DisplayServer.get_name() != "headless":
			await RenderingServer.frame_post_draw
			root.get_texture().get_image().save_png(OUT.path_join(entry[0]+"-main.png"))
	print("LOWPOLY_V02_MAIN_BINDINGS_AND_RENDER_PASS")
	quit()
