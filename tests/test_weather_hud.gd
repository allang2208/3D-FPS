extends SceneTree
var failures := 0
func _initialize() -> void:
	OS.set_environment("INVENTORY_SAVE_PATH", "user://weather-hud-layout-test.save")
	call_deferred("run")
func check(ok: bool, message: String) -> void:
	if not ok:
		failures += 1
		printerr("HUD FAIL: ", message)
func run() -> void:
	var hud = root.get_node("HUD")
	hud._ensure_built()
	var bar = hud.status_bar
	var sidebar = bar.get_node("OriginalSidebar/Menu")
	bar.set_hp(100,100)
	bar.set_mp(100,250)
	for dimensions in [Vector2i(1920,1080), Vector2i(1280,720), Vector2i(960,540), Vector2i(1920,1080)]:
		root.size = dimensions
		await create_timer(0.3).timeout
		bar.set_weapon_name("生锈的长剑")
		bar.set_ammo_enabled(false)
		bar.set_ammo(0,0)
		check(not bar._ammo_panel.visible, "melee must hide ammo")
		bar.set_weapon_name("AKM")
		bar.set_ammo_enabled(true)
		bar.set_ammo(30,90)
		await process_frame
		check(bar._ammo_panel.visible, "gun must show ammo")
		check(not bar._ammo_panel.get_global_rect().intersects(sidebar.get_global_rect()), "ammo overlaps navigation " + str(dimensions))
		check(not bar._ammo_panel.get_global_rect().intersects(hud.backpack_hud.get_node("Hotbar").get_global_rect()), "ammo overlaps hotbar")
		var weapon_card: Control = bar.get_node("WeaponReadout")
		for weapon_name in ["AKM", "生锈的长剑", "精密改装的长管突击步枪 · 荒野特别型", ""]:
			bar.set_weapon_name(weapon_name)
			await process_frame
			check(Rect2(Vector2.ZERO,Vector2(dimensions)).encloses(weapon_card.get_global_rect()),"weapon readout fits viewport")
			check(not weapon_card.get_global_rect().intersects(hud.backpack_hud.get_node("Hotbar").get_global_rect()),"weapon readout avoids hotbar")
			check(weapon_card.get_global_rect().size.x==160,"long weapon name cannot expand panel")
		check(bar._weapon_label.text=="空手","empty weapon name has readable fallback")
		bar.set_weapon_name("AKM")
		check(not bar._top_bar.get_global_rect().intersects(bar._clock_view.get_global_rect()), "clock overlaps top bar")
		bar.set_ammo(0,90)
		check(bar._ammo_panel.visible and bar._ammo_label.text == "0", "empty gun ammo must remain visible")
		bar.set_ammo_enabled(false)
		bar.show_status("建筑已保存",1.5)
		await process_frame
		check(bar._status_label.visible, "non-weapon messages must remain visible")
	bar.set_ammo_enabled(true)
	bar.reset_ammo_feedback()
	bar.set_ammo(30,120)
	check(bar._ammo_label.modulate==Color.WHITE,"initial binding does not flash")
	bar.set_ammo(29,120)
	var first_flash: Tween = bar._ammo_flash
	check(first_flash.is_running(),"shot starts number feedback")
	bar.set_ammo(28,120)
	check(not first_flash.is_valid(),"automatic fire replaces previous pulse")
	var second_flash: Tween = bar._ammo_flash
	bar.set_ammo(28,120)
	check(bar._ammo_flash==second_flash,"unchanged refresh does not restart pulse")
	await create_timer(0.25).timeout
	check(bar._ammo_label.modulate.is_equal_approx(Color.WHITE),"shot feedback settles")
	bar.set_ammo(30,118)
	check(not bar._ammo_flash.is_running() and bar._reserve_flash.is_running(),"reload pulses only depleted reserve")
	bar.reset_ammo_feedback()
	bar.set_ammo(7,50)
	check(bar._ammo_label.modulate==Color.WHITE and bar._ammo_reserve_label.modulate==Color.WHITE,"weapon switch does not fake consumption")
	bar.set_ammo(6,50)
	bar.set_ammo_enabled(false)
	check(not bar._ammo_flash.is_valid() and bar._ammo_label.modulate==Color.WHITE,"hiding ammo stops feedback")
	print("WEATHER HUD LAYOUT: ", failures, " failures; ammo/hotbar separation, melee/gun/empty, resize back, generic message")
	quit(1 if failures else 0)
