extends SceneTree

func _initialize() -> void:
	call_deferred("run")

func run() -> void:
	var preview_width := int(OS.get_environment("BACKPACK_PREVIEW_WIDTH")) if not OS.get_environment("BACKPACK_PREVIEW_WIDTH").is_empty() else 1280
	var preview_height := int(OS.get_environment("BACKPACK_PREVIEW_HEIGHT")) if not OS.get_environment("BACKPACK_PREVIEW_HEIGHT").is_empty() else 720
	var output_path := OS.get_environment("BACKPACK_PREVIEW_PATH")
	if output_path.is_empty():
		output_path = "res://docs/preview/backpack-spatial-16x8-720.png"
	root.size = Vector2i(preview_width, preview_height)
	var stage := Node3D.new()
	root.add_child(stage)
	current_scene = stage
	var hud := root.get_node("HUD")
	hud._ensure_built()
	hud.backpack.slots.fill(null)
	hud.backpack.add_instance(hud.item_db.create_instance("akm"), 0)
	hud.equipment.slots["weapon"] = hud.item_db.create_instance("akm")
	hud.equipment.changed.emit()
	hud.backpack.add_item("hp_potion", 5)
	hud.backpack.add_item("mp_potion", 3)
	hud.backpack.add_instance({"id":"gold", "name":"金币", "category":"gold", "rarity":"mythic", "icon_fallback":"💰", "stack":200, "stack_max":999, "instance_id":"preview-gold"})
	hud.backpack_hud.set_panel_open(true)
	for _frame in 30:
		await process_frame
	await RenderingServer.frame_post_draw
	root.get_texture().get_image().save_png(output_path)
	print("SPATIAL_PREVIEW grid=", hud.backpack_hud._grid.get_global_rect(), " used=", hud.backpack.used_cell_count(), "/", hud.backpack.max_slots)
	quit()
