extends SceneTree

const Spatial := preload("res://ui/spatial_inventory.gd")
const ReferenceStyle := preload("res://ui/backpack_reference_style.gd")

var failures := 0

func _initialize() -> void:
	call_deferred("run")

func check(ok: bool, label: String) -> void:
	print("TEST backpack_grid ", label, "=", ok)
	if not ok:
		failures += 1

func run() -> void:
	var db := preload("res://ui/item_db.gd").new()
	var bp := preload("res://ui/backpack.gd").new(db)
	var hud := preload("res://ui/backpack_hud.gd").new()
	root.add_child(hud)
	check(hud._cells.is_empty(), "no_placeholder_slots_before_binding")
	hud.setup(bp, null)
	check(bp.grid_columns == 16 and bp.grid_rows == 8, "model_is_16x8")
	check(hud._cells.size() == 128 and hud._grid.get_child_count() == 128, "hud_is_16x8")
	var rifle: Dictionary = {"id":"akm", "name":"AKM", "category":"weapon_ranged", "weaponType":"akm", "isTwoHanded":true, "equipSlot":"weapon", "rarity":"common", "stack":1, "stack_max":1, "instance_id":"rifle-1"}
	rifle.instance_id = "rifle-1"
	var icon_resolver := preload("res://ui/item_icon.gd")
	for weapon_id in ["akm", "qbz191"]:
		var weapon := {"id":weapon_id, "category":"weapon_ranged", "stack":1}
		var expected: String = "res://assets/ui/icons/equip/gunsmith/fps_" + str(weapon_id) + "_gunsmith.png"
		check(icon_resolver.backpack_path(weapon) == expected, "backpack_reuses_current_gunsmith_" + weapon_id)
		check(load(expected) is Texture2D, "gunsmith_backpack_texture_loads_" + weapon_id)
	check(icon_resolver.equipment_path(rifle) == "res://assets/ui/icons/equip/fps_akm.png", "equipment_uses_upward_diagonal_art")
	check(bp.add_instance(rifle, 0), "place_rifle")
	await process_frame
	check(bp.used_cell_count() == 16 and bp.item_count() == 1, "rifle_occupies_8x2")
	check(Vector2i(int(bp.slots[0].grid_w), int(bp.slots[0].grid_h)) == Vector2i(8, 2), "rifle_size_saved")
	var grid_side: float = hud._cells[33].position.x - hud._cells[32].position.x
	check(is_equal_approx(hud._cells[0].size.x, 8.0 * grid_side) and is_equal_approx(hud._cells[0].size.y, 2.0 * grid_side), "rifle_uses_rescaled_8x2_footprint")
	check(hud._cells[1].visible and hud._cells[23].visible, "covered_cells_remain_visible_beneath_item_card")
	check(hud._cells[1].mouse_filter == Control.MOUSE_FILTER_IGNORE, "covered_cells_do_not_capture_input")
	var column_step: float = hud._cells[33].position.x - hud._cells[32].position.x
	var row_step: float = hud._cells[48].position.y - hud._cells[32].position.y
	check(is_equal_approx(column_step, row_step) and is_equal_approx(hud._cells[32].size.x, hud._cells[32].size.y), "backpack_cells_are_geometrically_square")
	check(is_equal_approx(hud._cells[32].size.x, hud._grid.size.x / 16.0), "backpack_cell_width_and_height_are_half_previous_size")
	check(is_equal_approx(hud._cells[47].position.x + hud._cells[47].size.x, hud._grid.size.x), "sixteen_columns_fill_backpack_width")
	check(is_equal_approx(hud._cells[32].position.x, 0.0), "rescaled_grid_starts_at_left_edge")
	var grid_backing := hud._grid.get_theme_stylebox("panel") as StyleBoxFlat
	check(grid_backing != null and grid_backing.bg_color.is_equal_approx(ReferenceStyle.BACKPACK_EMPTY_BOTTOM), "fractional_grid_seams_use_backpack_surface")
	var empty_style := hud._cells[32].get_theme_stylebox("panel") as StyleBoxTexture
	var item_style := hud._cells[0].get_theme_stylebox("panel") as StyleBoxTexture
	var covered_style := hud._cells[1].get_theme_stylebox("panel") as StyleBoxTexture
	check(empty_style != null and item_style != null and empty_style.texture != item_style.texture, "empty_and_occupied_surfaces_differ")
	var empty_image := empty_style.texture.get_image()
	var item_image := item_style.texture.get_image()
	var covered_image := covered_style.texture.get_image()
	check(empty_image.get_pixel(0, 0).get_luminance() > empty_image.get_pixel(127, 127).get_luminance(), "empty_slot_has_raised_edges")
	check(item_image.get_pixel(0, 0).get_luminance() < item_image.get_pixel(127, 127).get_luminance(), "occupied_slot_has_pressed_edges")
	check(absf(empty_image.get_pixel(0, 64).get_luminance() - empty_image.get_pixel(127, 64).get_luminance()) < 0.20, "empty_slot_seam_is_low_contrast")
	check(absf(empty_image.get_pixel(0, 64).get_luminance() - empty_image.get_pixel(1, 64).get_luminance()) > 0.01, "empty_slot_edge_is_one_pixel")
	check(item_image.get_pixel(64, 64).a < covered_image.get_pixel(64, 64).a, "item_card_is_transparent_over_pressed_cells")
	check(hud._cells[0].get_node_or_null("Content/TechnicalFrame") == null, "slot_has_no_extra_technical_overlays")
	check(is_equal_approx(hud._cells[0].get_node("Content/Icon").modulate.a, 0.82), "occupied_item_is_semitransparent")
	check(not hud._cells[0].get_node("Content/Rarity").visible and not hud._cells[0].get_node("Content/Name").visible, "firearm_overlays_hidden")
	check(hud._cells[0].get_node("Content/Icon").texture is AtlasTexture, "firearm_transparent_margins_cropped")
	var rifle_atlas := hud._cells[0].get_node("Content/Icon").texture as AtlasTexture
	check(rifle_atlas != null and rifle_atlas.atlas.resource_path == "res://assets/ui/icons/equip/gunsmith/fps_akm_gunsmith.png", "hud_backpack_uses_current_gunsmith_akm")
	var grab_cell := Vector2i(2, 1)
	var drag_data := {"type": "backpack", "slot": 0, "item": rifle.duplicate(true), "grab_cell": grab_cell}
	var hovered_cell := Spatial.anchor_index(Vector2i(6, 3))
	check(hud.drag_target_anchor(hovered_cell, drag_data) == Spatial.anchor_index(Vector2i(4, 2)), "drag_keeps_grabbed_cell_under_pointer")
	hud.set_cell_drag_over(hovered_cell, true, drag_data)
	check(hud._drag_over_cells.size() == 16 and hud._drag_over_cells.has(36) and hud._drag_over_cells.has(59), "drag_depresses_full_8x2_target_footprint")
	check(hud._drag_over_valid, "clear_full_footprint_is_valid_drop_target")
	var drag_preview := hud.make_slot_preview(rifle, grab_cell, true)
	var drag_visual := drag_preview.get_node("Overlay/SpatialVisual") as Control
	var drag_tiles := drag_visual.get_node("FootprintCells") as Control
	check(drag_tiles.get_child_count() == 16, "drag_ghost_contains_full_8x2_cell_surface")
	check(is_equal_approx(drag_visual.size.x, 8.0 * grid_side) and is_equal_approx(drag_visual.size.y, 2.0 * grid_side), "drag_ghost_matches_item_footprint_size")
	check(is_equal_approx(drag_visual.position.x, -(2.5 * grid_side)) and is_equal_approx(drag_visual.position.y, -(1.5 * grid_side)), "drag_ghost_uses_grabbed_cell_as_cursor_pivot")
	var drag_icon_texture := (drag_visual.get_node("Icon") as TextureRect).texture as AtlasTexture
	check(drag_icon_texture != null and drag_icon_texture.atlas.resource_path == "res://assets/ui/icons/equip/gunsmith/fps_akm_gunsmith.png", "drag_ghost_reuses_current_gunsmith_texture")
	drag_preview.free()
	hud.set_cell_drag_over(hovered_cell, false)
	hud.drop_on_backpack(Spatial.anchor_index(Vector2i(4, 2)), drag_data)
	check(bp.slots[Spatial.anchor_index(Vector2i(4, 2))] != null and bp.slots[0] == null, "grab_offset_drop_moves_whole_item_to_previewed_anchor")
	hud.drop_on_backpack(0, drag_data)
	check(bp.slots[0] != null and bp.slots[Spatial.anchor_index(Vector2i(4, 2))] == null, "dragged_item_can_return_without_data_loss")
	var edge_hover := Spatial.anchor_index(Vector2i.ZERO)
	hud.set_cell_drag_over(edge_hover, true, drag_data)
	check(not hud._drag_over_valid and hud._drag_over_cells.size() == 6, "out_of_bounds_drag_shows_clipped_full_footprint_as_invalid")
	hud.set_cell_drag_over(edge_hover, false)
	var source_badge := hud._cells[0].get_node("Content").get_node_or_null("SourceBadge0") as Control
	check(source_badge == null or not source_badge.visible, "enhance_craft_enchant_badges_hidden")
	check(not preload("res://ui/spatial_inventory.gd").can_place(bp.slots, rifle, 1), "occupied_cells_reject_overlap")

	var potion := {"id":"potion", "name":"药剂", "category":"consumable", "stack":1, "stack_max":5, "rarity":"common", "instance_id":"potion-1"}
	check(bp.add_instance(potion, 32), "place_one_cell_item")
	check(bp.used_cell_count() == 17 and bp.item_count() == 2, "mixed_footprints_count")
	var refill := potion.duplicate(true)
	refill.instance_id = "potion-2"
	refill.stack = 4
	check(bp.add_instance(refill) and int(bp.slots[32].stack) == 5, "spatial_metadata_does_not_block_stacking")
	var saved := bp.serialize()
	var restored := preload("res://ui/backpack.gd").new(null)
	restored.restore(saved)
	check(restored.slots[0] != null and restored.slots[32] != null, "restore_preserves_anchors")
	check(restored.used_cell_count() == 17, "restore_preserves_occupancy")

	hud.queue_free()
	await process_frame
	print("TEST backpack_grid failures=", failures)
	quit(0 if failures == 0 else 1)
