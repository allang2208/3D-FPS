extends SceneTree
func _initialize() -> void:
	call_deferred("run")
func run() -> void:
	root.size = Vector2i(1912, 948)
	var stage := Node3D.new()
	root.add_child(stage)
	current_scene = stage
	var hud := root.get_node("HUD")
	hud._ensure_built()
	hud.backpack.slots.fill(null)
	hud.backpack.add_item("hp_potion", 5)
	hud.backpack.add_item("mp_potion", 3)
	hud.backpack.add_instance({"id":"gold", "name":"金币", "category":"gold", "rarity":"mythic", "icon_fallback":"💰", "stack":200})
	for key in hud.equipment.slots:
		hud.equipment.slots[key] = null
	hud.equipment.slots.weapon = hud.item_db.create_instance("rusty_sword")
	hud.equipment.changed.emit()
	hud.backpack_hud.set_panel_open(true)
	for i in 40:
		await process_frame
	await RenderingServer.frame_post_draw
	root.get_texture().get_image().save_png("res://docs/preview/backpack-reference-1912.png")
	print("REFERENCE: panel=", hud.backpack_hud._panel.get_global_rect(), " equipment=", hud.backpack_hud._equip_grid.get_global_rect(), " inventory=", hud.backpack_hud._grid.get_global_rect())
	root.size = Vector2i(1280, 720)
	for i in 20:
		await process_frame
	await RenderingServer.frame_post_draw
	root.get_texture().get_image().save_png("res://docs/preview/backpack-reference-720.png")
	quit()
