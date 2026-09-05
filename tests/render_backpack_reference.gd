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
	var font := preload("res://ui/style.gd").make_font()
	for rid in font.get_rids():
		print("FONT FACE: ", TextServerManager.get_primary_interface().font_get_face_index(rid), " ", TextServerManager.get_primary_interface().font_get_name(rid))
	hud.backpack.slots.fill(null)
	hud.backpack.add_item("hp_potion", 5)
	hud.backpack.add_item("mp_potion", 3)
	hud.backpack.add_instance({"id":"gold", "name":"金币", "category":"gold", "rarity":"mythic", "icon_fallback":"💰", "stack":200})
	for key in hud.equipment.slots:
		hud.equipment.slots[key] = null
	hud.equipment.slots.weapon = hud.item_db.create_instance("rusty_sword")
	hud.equipment.changed.emit()
	for frame in 25:
		await process_frame
	await RenderingServer.frame_post_draw
	root.get_texture().get_image().save_png("res://docs/preview/original-sidebar-1912.png")
	hud.backpack_hud.set_panel_open(true)
	await create_timer(0.4).timeout
	for label in [hud.backpack_hud._cells[0].get_node("Content/Name"), hud.backpack_hud._equip_cells.weapon.get_node("Content/Name")]:
		var actual: Font = label.get_theme_font("font")
		print("ITEM FONT: ", label.text, " = ", actual.get_font_name(), " size=", label.get_theme_font_size("font_size"))
	await RenderingServer.frame_post_draw
	root.get_texture().get_image().save_png("res://docs/preview/backpack-reference-1912.png")
	print("REFERENCE: panel=", hud.backpack_hud._panel.get_global_rect(), " equipment=", hud.backpack_hud._equip_grid.get_global_rect(), " inventory=", hud.backpack_hud._grid.get_global_rect())
	root.size = Vector2i(1280, 720)
	for i in 20:
		await process_frame
	await RenderingServer.frame_post_draw
	root.get_texture().get_image().save_png("res://docs/preview/backpack-reference-720.png")
	quit()
