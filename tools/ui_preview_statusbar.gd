extends SceneTree
## 状态栏 HUD 预览截图
## 运行： $godot --path 'E:\3d\3-dfps' --script res://tools/ui_preview_statusbar.gd

const StatusBarScript := preload("res://ui/status_bar.gd")

const OUT := "C:/Users/allan/AppData/Local/Temp/ui_preview_statusbar.png"

func _initialize() -> void:
	root.size = Vector2i(1920, 1080)
	var bar := StatusBarScript.new()
	root.add_child(bar)
	await process_frame
	await process_frame
	bar.set_hp(20, 100)
	bar.set_mp(46, 100)
	bar.set_ammo(24, 96)
	bar.set_weapon_name("AK-74 突击步枪")
	bar.set_kills(7)
	for i in 6:
		await process_frame
	print("ammo_label: visible=", bar.get("_ammo_label").visible,
		" text=[", bar.get("_ammo_label").text, "] pos=", bar.get("_ammo_label").global_position,
		" color=", bar.get("_ammo_label").get_theme_color("font_color"))
	var ammo: Label = bar.get("_ammo_label")
	print("anchor=", ammo.anchor_left, "/", ammo.anchor_top, "/", ammo.anchor_right, "/", ammo.anchor_bottom,
		" offsets=", ammo.offset_left, "/", ammo.offset_top, "/", ammo.offset_right, "/", ammo.offset_bottom)
	print("viewport size=", root.get_visible_rect().size)
	print("weapon_label: visible=", bar.get("_weapon_label").visible,
		" text=[", bar.get("_weapon_label").text, "] pos=", bar.get("_weapon_label").global_position)
	print("reserve_label: visible=", bar.get("_ammo_reserve_label").visible,
		" text=[", bar.get("_ammo_reserve_label").text, "] pos=", bar.get("_ammo_reserve_label").global_position)
	await RenderingServer.frame_post_draw
	var img := root.get_texture().get_image()
	img.save_png(OUT)
	print("saved ", OUT)
	quit()
