extends SceneTree
var output := OS.get_environment("UI_AUDIT_OUTPUT")
func _initialize() -> void:
	call_deferred("run")
func run() -> void:
	var hud = root.get_node("HUD")
	hud._ensure_built()
	await process_frame
	hud.set_process(false)
	for i in hud.backpack.slots.size():
		var item = hud.backpack.slots[i]
		if item != null and item.get("id") == "hp_potion":
			hud.backpack.bind_hotbar(0, item.instance_id)
		if item != null and item.get("id") == "mp_potion":
			hud.backpack.bind_hotbar(1, item.instance_id)
	DisplayServer.window_set_mode(DisplayServer.WINDOW_MODE_WINDOWED)
	var ui = hud.backpack_hud
	var bar = ui.get_node("Hotbar")
	for resolution in [Vector2i(1920,1080), Vector2i(1280,720), Vector2i(960,540)]:
		root.size = resolution
		root.content_scale_size = resolution
		await create_timer(0.3).timeout
		for slot in ui._skill_slots + ui._hotbar_slots:
			assert(slot.size == Vector2(48,48), "Shortcut slot must stay square")
			assert(bar.get_global_rect().encloses(slot.get_global_rect()), "Slot exceeds shell")
		assert(absf(bar.get_global_rect().get_center().x - resolution.x / 2.0) < 1, "Dock must be centered")
		assert(bar.get_global_rect().end.y <= resolution.y - 11, "Bottom clearance")
		await RenderingServer.frame_post_draw
		root.get_texture().get_image().save_png(output.path_join("hotbar-%d.png" % resolution.x))
		var crop := root.get_texture().get_image().get_region(Rect2i(bar.get_global_rect().grow(12)))
		crop.save_png(output.path_join("hotbar-detail.png"))
	# Drag-binding still swaps the original instances.
	var first = hud.backpack.resolve_hotbar(0)
	ui.drop_on_hotbar(1, {"type":"hotbar", "index":0})
	assert(hud.backpack.resolve_hotbar(1).instance_id == first.instance_id)
	print("HOTBAR: square slots, shell bounds, centering at 3 sizes, binding swap PASS")
	quit()
