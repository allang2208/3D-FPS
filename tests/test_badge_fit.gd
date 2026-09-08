extends SceneTree
const Ref = preload("res://ui/backpack_reference_style.gd")
var output := OS.get_environment("UI_AUDIT_OUTPUT")
var failures := 0
func _initialize() -> void:
	assert(not OS.get_environment("INVENTORY_SAVE_PATH").is_empty())
	call_deferred("run")
func check(ok: bool, message: String) -> void:
	if not ok:
		push_error(message)
		failures += 1
func run() -> void:
	await process_frame
	DisplayServer.window_set_mode(DisplayServer.WINDOW_MODE_WINDOWED)
	root.size = Vector2i(1920, 1080)
	root.content_scale_size = root.size
	var hud = root.get_node("HUD")
	hud._ensure_built()
	await process_frame
	DisplayServer.window_set_mode(DisplayServer.WINDOW_MODE_WINDOWED)
	root.size = Vector2i(1920, 1080)
	root.content_scale_size = root.size
	hud.set_process(false)
	var layer := CanvasLayer.new()
	layer.layer = 200
	root.add_child(layer)
	var layout := VBoxContainer.new()
	layout.position = Vector2(40, 60)
	layout.add_theme_constant_override("separation", 12)
	layer.add_child(layout)
	var title := Label.new()
	title.text = "四类词条 · 实际组件检查"
	title.add_theme_font_override("font", preload("res://ui/style.gd").make_font())
	title.add_theme_font_size_override("font_size", 24)
	layout.add_child(title)
	var cells: Array = []
	for rarity in ["common", "uncommon", "rare", "epic", "mythic", "legendary"]:
		var row := HBoxContainer.new()
		row.add_theme_constant_override("separation", 16)
		layout.add_child(row)
		for script in ["res://ui/item_cell.gd", "res://ui/warehouse_cell.gd"]:
			var item = hud.item_db.create_instance("fps_akm" if hud.item_db.has_item("fps_akm") else "knights_sword")
			assert(not item.is_empty(), "Preview item missing")
			item.rarity = rarity
			item.enhanceLevel = 10
			item._craftData = {"test": true}
			item._enchantData = {"prefix": {"name": "锋利"}}
			item.stack = 5
			var cell = load(script).new()
			cell.setup(item, Vector2(310, 64))
			row.add_child(cell)
			cells.append(cell)
	var weapon = hud.item_db.create_instance("fps_akm" if hud.item_db.has_item("fps_akm") else "knights_sword")
	weapon.rarity = "legendary"
	weapon.enhanceLevel = 10
	weapon._craftData = {"test": true}
	weapon._enchantData = {"prefix": {"name": "锋利"}}
	for key in hud.equipment.slots:
		hud.equipment.slots[key] = weapon.duplicate(true)
	hud.equipment.changed.emit()
	hud.backpack_hud.set_panel_open(true)
	hud.backpack_hud.set_tab("equip")
	await create_timer(0.6).timeout
	for cell in cells:
		for i in 3:
			var badge = cell.get_node("SourceBadge%d" % i)
			check(badge.visible, "processing flag missing")
			check(Rect2(Vector2.ZERO, cell.size).encloses(badge.get_rect()), "badge outside cell")
			check(badge.offset_top == 4 and badge.offset_bottom == -4, "vertical inset")
		check(cell._rarity_bar.get_theme_stylebox("panel").corner_radius_top_left == 4, "rarity roundness")
	# Rebuilding a card in the same frame must not reuse queued old badges.
	var reused = cells[0]
	reused.set_item({"name": "普通物品", "rarity": "common"})
	for i in 3:
		check(not reused.get_node("SourceBadge%d" % i).visible, "stale processing badge")
	check(Ref.has_enchantment({"_enchantData": {"suffix": {"name": "力量"}}}), "suffix detection")
	if not output.is_empty():
		DirAccess.make_dir_recursive_absolute(output)
		await RenderingServer.frame_post_draw
		root.get_texture().get_image().save_png(output.path_join("badge-fit.png"))
	# Exercise every combination and the alternate persisted modifier fields.
	for mask in 8:
		var data := {"name": "组合检查", "rarity": "rare", "enhanceLevel": 1 if mask & 1 else 0,
			"gunsmith_parts": {"optic": true} if mask & 2 else {},
			"_enchantData": {"suffix": {"name": "力量"}} if mask & 4 else {}}
		reused.set_item(data)
		for i in 3:
			check(reused.get_node("SourceBadge%d" % i).visible == bool(mask & (1 << i)), "modifier combination %d/%d" % [mask, i])
	layer.hide()
	root.size = Vector2i(1280, 720)
	root.content_scale_size = root.size
	await create_timer(0.5).timeout
	if not output.is_empty():
		await RenderingServer.frame_post_draw
		root.get_texture().get_image().save_png(output.path_join("badge-fit-1280.png"))
	root.size = Vector2i(960, 540)
	root.content_scale_size = root.size
	await create_timer(0.5).timeout
	for cell in hud.backpack_hud._equip_cells.values():
		var content = cell.get_node("Content")
		for name in ["Rarity", "SourceBadge0", "SourceBadge1", "SourceBadge2"]:
			var badge = content.get_node(name)
			if badge.visible:
				check(Rect2(Vector2.ZERO, content.size).encloses(badge.get_rect()), "compact equipment badge outside")
	if not output.is_empty():
		await RenderingServer.frame_post_draw
		root.get_texture().get_image().save_png(output.path_join("badge-fit-960.png"))
	print("BADGE FIT: ", failures, " failures")
	quit(1 if failures else 0)
