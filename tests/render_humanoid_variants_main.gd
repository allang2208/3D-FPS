extends SceneTree
var OUT := ProjectSettings.globalize_path("res://tools/ai-gen/humanoid-detail-v02-20260906/runtime-variants")
func _initialize() -> void:
	call_deferred("run_review")
func run_review() -> void:
	var main = load("res://scenes/main.tscn").instantiate()
	root.add_child(main)
	current_scene = main
	root.get_node("HUD").ensure_for_current_scene()
	await process_frame
	var miner = main.get_node("MinerWorkwearZombie")
	var runner = main.get_node("RunnerZombie")
	assert(miner._player == main.get_node("Player") and runner._player == main.get_node("Player"))
	assert(miner._model.scene_file_path.ends_with("miner_zombie_v02.glb"))
	assert(runner._model.scene_file_path.ends_with("runner_zombie_v02.glb"))
	for child in main.get_children():
		if child is CharacterBody3D:
			child.set_physics_process(false)
			if child != miner and child != runner: child.hide()
	miner.position = Vector3(-5, 0, -4)
	runner.position = Vector3(-2.8, 0, -4)
	miner.rotation.y = 0
	runner.rotation.y = 0
	var cam := Camera3D.new()
	main.add_child(cam)
	cam.current = true
	cam.fov = 43
	cam.global_position = Vector3(-6.7, 2.4, 1.2)
	cam.look_at(Vector3(-3.9, .95, -4))
	DirAccess.make_dir_recursive_absolute(OUT)
	for entry in [["Idle", .4], ["Walk", .6], ["Attack", .65], ["Death", 2.4]]:
		miner._sync_pose(entry[0], entry[1])
		runner._sync_pose(entry[0], entry[1])
		for i in 4: await process_frame
		if DisplayServer.get_name() != "headless":
			await RenderingServer.frame_post_draw
			root.get_texture().get_image().save_png(OUT.path_join(entry[0]+"-main.png"))
	print("HUMANOID_MAIN_RENDER_AND_BINDINGS_PASS")
	quit()
