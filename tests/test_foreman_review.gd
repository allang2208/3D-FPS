extends SceneTree
func _initialize() -> void:
	root.size = Vector2i(1280,720)
	call_deferred("run")
func run() -> void:
	var scene = load("res://scenes/wilderness_combat_study.tscn").instantiate()
	scene.automated = true
	root.add_child(scene)
	current_scene = scene
	var started := Time.get_ticks_msec()
	while not scene.prepared or scene.actors.get_child_count() < 4:
		await process_frame
		if Time.get_ticks_msec()-started > 180000:
			push_error("Foreman review setup timed out")
			quit(1)
			return
	await create_timer(1.4).timeout
	var enemy = scene.actors.get_node("ForemanReview")
	var ok: bool = enemy._ap.has_animation("IdleLoose") and enemy._skeleton.get_bone_count() == 85 and enemy._buffs.has("inspire")
	for i in range(1,4):
		var ally = scene.actors.get_node("RallyAlly%d" % i)
		print("RALLY_CHECK ",i," buff=",ally._buffs.has("inspire"))
		ok = ok and ally._buffs.has("inspire")
	if DisplayServer.get_name() != "headless":
		await RenderingServer.frame_post_draw
		root.get_texture().get_image().save_png("user://foreman-review.png")
	print("FOREMAN_REVIEW verified=",ok," state=",enemy.combat_state," hp=",enemy._hp," bones=",enemy._skeleton.get_bone_count())
	quit(0 if ok else 1)
