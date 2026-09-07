extends SceneTree

const Spatial := preload("res://ui/spatial_inventory.gd")

func _initialize() -> void:
	call_deferred("run")

func run() -> void:
	root.size = Vector2i(1280, 720)
	var stage := Node3D.new()
	root.add_child(stage)
	current_scene = stage
	var hud := root.get_node("HUD")
	hud._ensure_built()
	hud.backpack.slots.fill(null)
	hud.backpack.add_instance(hud.item_db.create_instance("akm"), 0)
	hud.backpack.add_item("hp_potion", 5)
	hud.backpack_hud.set_panel_open(true)
	for _frame in 30:
		await process_frame
	var item: Dictionary = hud.backpack.slots[0]
	var grab_cell := Vector2i(3, 1)
	var hovered_cell := Spatial.anchor_index(Vector2i(10, 4))
	var data := {"type": "backpack", "slot": 0, "item": item.duplicate(true), "grab_cell": grab_cell}
	hud.backpack_hud.set_cell_drag_over(hovered_cell, true, data)
	hud.backpack_hud._cells[0].modulate.a = 0.3
	var preview: Control = hud.backpack_hud.make_slot_preview(item, grab_cell, true)
	hud.backpack_hud.add_child(preview)
	preview.global_position = hud.backpack_hud._cells[hovered_cell].get_global_rect().get_center()
	for _frame in 4:
		await process_frame
	await RenderingServer.frame_post_draw
	root.get_texture().get_image().save_png("res://docs/preview/backpack-spatial-drag-8x2-720.png")
	print("SPATIAL_DRAG_PREVIEW footprint=", Spatial.footprint(item), " highlighted=", hud.backpack_hud._drag_over_cells.size(), " target=", hud.backpack_hud._drag_over_cell)
	quit()
