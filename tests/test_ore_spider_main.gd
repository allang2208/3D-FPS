extends SceneTree
func _initialize() -> void:
	OS.set_environment("INVENTORY_SAVE_PATH", "user://ore-release-%d.save" % Time.get_ticks_usec())
	call_deferred("run")
func run() -> void:
	var main: Node3D = load("res://scenes/main.tscn").instantiate()
	root.add_child(main)
	current_scene = main
	for i in 180: await physics_frame
	var spider = main.get_node("OreSpider")
	assert(spider.hand_throw)
	assert(spider.get_node("Model").scene_file_path.ends_with("ore_spider_v07_preview.glb"))
	assert(spider.max_hp == 650 and spider._skeleton.find_bone("arm_hand") >= 0)
	print("ORE_MAIN PASS: 180 physics frames, approved model and hand throw")
	main.queue_free()
	for i in 3: await process_frame
	quit()
