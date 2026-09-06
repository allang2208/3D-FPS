extends SceneTree
func _initialize() -> void:
	OS.set_environment("WILDERNESS_SAVE_PATH","user://basic-tools-render-"+str(OS.get_process_id())+".json")
	OS.set_environment("INVENTORY_SAVE_PATH","user://basic-tools-render-inventory-"+str(OS.get_process_id())+".save")
	call_deferred("run")
func run() -> void:
	var scene: Node3D=load("res://scenes/scenic_valley.tscn").instantiate()
	root.add_child(scene)
	current_scene=scene
	var editor: Node=scene.get_node("WildernessEditor")
	editor.player.set_physics_process(false)
	editor.player.set_process_unhandled_input(false)
	editor.camera.get_node("CameraFx").process_mode=Node.PROCESS_MODE_DISABLED
	editor.set_enabled(true)
	for i in 90: await process_frame
	for kind in ["axe","pickaxe"]:
		editor.toolkit.equip(kind)
		for i in 3: await process_frame
		await RenderingServer.frame_post_draw
		root.get_texture().get_image().save_png("E:/3d/3-dfps/tools/basic-tools/"+kind+"-gameplay.png")
		editor.toolkit.pivot.rotation=Vector3(-0.95,0,0.247)
		for i in 3: await process_frame
		await RenderingServer.frame_post_draw
		root.get_texture().get_image().save_png("E:/3d/3-dfps/tools/basic-tools/"+kind+"-contact.png")
	editor.set_enabled(false)
	root.get_node("HUD").process_mode=Node.PROCESS_MODE_DISABLED
	scene.free()
	quit()
