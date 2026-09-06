extends SceneTree
const Loader = preload("res://ui/loading_screen.gd")
func _initialize(): call_deferred("run")
func run():
	assert(OS.has_environment("INVENTORY_SAVE_PATH"))
	var loader = Loader.new()
	root.add_child(loader)
	for transition in 2:
		Loader.load_scene("res://tests/fixtures/loading_delayed.tscn")
		var saw_pending := false
		while loader._loading:
			if current_scene != null and not current_scene.is_loading_ready():
				saw_pending = true
				assert(loader._root.visible and loader._bar.value < 100 and paused)
			await process_frame
		assert(saw_pending and current_scene.is_loading_ready())
		assert(Loader.instance == loader and loader.get_parent() == root)
		assert(not loader._root.visible and not paused and loader._bar.value == 100)
		print("PASS delayed initialization remains covered, transition ",transition)
	quit()
