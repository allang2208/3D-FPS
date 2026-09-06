extends SceneTree
func _initialize() -> void:
	OS.set_environment("INVENTORY_SAVE_PATH","user://foreman-entry-%d.save" % Time.get_ticks_usec())
	call_deferred("run_test")
func run_test() -> void:
	root.get_node("HUD")._ensure_built()
	var main=load("res://scenes/main.tscn").instantiate()
	root.add_child(main)
	current_scene=main
	for i in range(20):await process_frame
	var gate=main.get_node_or_null("ForemanPracticePortal")
	if gate==null:
		push_error("Main scene missing foreman portal")
		quit(1)
		return
	gate._on_body_entered(main._player)
	for i in range(900):
		await process_frame
		if is_instance_valid(current_scene) and current_scene.name=="ForemanDemo":break
	for i in range(12):await physics_frame
	var ok: bool=current_scene.name=="ForemanDemo" and current_scene.has_node("ForemanZombie") and current_scene._gun.reserve==600
	print("FOREMAN_ENTRY portal_transition=",ok)
	current_scene.queue_free()
	await process_frame
	quit(0 if ok else 1)
