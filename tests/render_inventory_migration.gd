extends SceneTree

func _initialize() -> void:
	call_deferred("run")

func run() -> void:
	var stage := Node3D.new()
	stage.name = "InventoryPreview"
	root.add_child(stage)
	current_scene = stage
	root.size = Vector2i(1920, 1080)
	var hud := root.get_node("HUD")
	hud._ensure_built()
	hud.backpack.add_item("enhancement_stone", 120)
	hud.backpack.add_item("reforge_ticket", 25)
	hud.backpack.add_item("rusty_sword", 1)
	var sample: Dictionary = hud.backpack.slots[4]
	if sample != null:
		sample.enhanceLevel = 3
	hud.backpack.changed.emit()
	hud.backpack_hud.set_panel_open(true)
	for frame in 45:
		await process_frame
	await RenderingServer.frame_post_draw
	root.get_texture().get_image().save_png("res://docs/preview/inventory-cold-steel-1080.png")
	print("INVENTORY_RENDER: panel=", hud.backpack_hud._panel.get_global_rect(), " grid=", hud.backpack_hud._grid.get_global_rect())
	root.size = Vector2i(1280, 720)
	for frame in 30:
		await process_frame
	await RenderingServer.frame_post_draw
	root.get_texture().get_image().save_png("res://docs/preview/inventory-cold-steel-720.png")
	print("INVENTORY_RENDER_720: panel=", hud.backpack_hud._panel.get_global_rect(), " grid=", hud.backpack_hud._grid.get_global_rect())
	hud.backpack_hud.set_panel_open(false)
	var panels := preload("res://ui/npc_panels.gd").build(stage, hud.item_db, hud.backpack, hud.equipment, hud.economy, null, hud.warehouse, hud.player_status)
	panels.warehouse.open_panel()
	for frame in 30:
		await process_frame
	await RenderingServer.frame_post_draw
	root.get_texture().get_image().save_png("res://docs/preview/warehouse-cold-steel-720.png")
	quit()
