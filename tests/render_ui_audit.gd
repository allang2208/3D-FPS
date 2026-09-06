extends SceneTree
func _initialize() -> void:
	call_deferred("run")
func run() -> void:
	root.size = Vector2i(1280, 720)
	var stage := Node3D.new()
	root.add_child(stage)
	current_scene = stage
	var hud := root.get_node("HUD")
	hud._ensure_built()
	var panels := preload("res://ui/npc_panels.gd").build(stage, hud.item_db, hud.backpack, hud.equipment, hud.economy, null, hud.warehouse, hud.player_status)
	var phase := "before" if "--before" in OS.get_cmdline_user_args() else "after"
	for tab in ["status", "equip", "skill", "codex"]:
		hud.backpack_hud.set_panel_open(true)
		hud.backpack_hud.set_tab(tab)
		await capture(phase + "-" + tab)
	hud.backpack_hud.set_panel_open(false)
	for key in panels:
		panels[key].open_panel()
		await capture(phase + "-" + key)
		panels[key].close()
		assert(not panels[key]._tooltip.visible, "Closed panel left tooltip visible")
	quit()
func capture(name: String) -> void:
	await create_timer(0.35).timeout
	await RenderingServer.frame_post_draw
	root.get_texture().get_image().save_png("res://docs/preview/ui-audit/" + name + ".png")
	print("AUDIT CAPTURE: ", name)
