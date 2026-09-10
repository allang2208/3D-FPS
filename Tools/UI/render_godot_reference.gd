extends SceneTree

func _initialize() -> void:
	call_deferred("run")

func run() -> void:
	var hud = root.get_node("HUD")
	hud._ensure_built()
	var bp: Control = hud.backpack_hud
	bp.set_tab("status")
	bp.set_panel_open(true)
	for dimensions in [Vector2i(1280, 720), Vector2i(960, 540), Vector2i(1920, 1080)]:
		root.size = dimensions
		await create_timer(0.6).timeout
		await RenderingServer.frame_post_draw
		var path := "D:/FPS3D/FPSGAME/Saved/UIUpgrade/2026-09-09/godot-status-%dx%d.png" % [dimensions.x, dimensions.y]
		root.get_texture().get_image().save_png(path)
	print("GODOT_REFERENCE_CAPTURE_COMPLETE")
	quit()
