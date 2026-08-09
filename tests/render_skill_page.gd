extends SceneTree
## 技能页（K 面板）实拍：验证槽位图标/名称/冷却 + 修炼列表
## 运行：$godot --rendering-driver opengl3 --path 'E:\3d\3-dfps' --script res://tests/render_skill_page.gd
var _frames := 0

func _process(_delta: float) -> bool:
	_frames += 1
	if _frames == 1:
		_build_hud()
	if _frames == 20:
		var bph := root.find_child("BackpackHud", true, false)
		if bph != null:
			bph.set_tab("skill")
			bph.set_panel_open(true)
	if _frames == 80:
		var bph2 := root.find_child("BackpackHud", true, false)
		if bph2 != null:
			print("PANEL open=", bph2.get("_panel_open"), " tab=", bph2.get("_current_tab"),
				" root_visible=", bph2.get_node_or_null("_panel_root").visible if bph2.get_node_or_null("_panel_root") != null else "?",
				" page_visible=", bph2.get_node_or_null("SkillPage").visible if bph2.get_node_or_null("SkillPage") != null else "?")
			var sp: Node = bph2.find_child("SkillPage", true, false)
			if sp != null:
				print("SKILLPAGE rows=", sp.get("_train_rows").size(), " vbox_children=", sp.get("_vbox").get_child_count(),
					" db_skills=", sp.get("_db").skills.size() if sp.get("_db") != null else "?")
		var img := root.get_viewport().get_texture().get_image()
		if img != null and img.get_width() > 0:
			img.save_png("res://docs/preview/ui_skill_page.png")
			print("SAVED ", ProjectSettings.globalize_path("res://docs/preview/ui_skill_page.png"))
		quit(0)
		return true
	return false

func _build_hud() -> void:
	var item_db = load("res://ui/item_db.gd").new()
	var backpack = load("res://ui/backpack.gd").new(item_db)
	backpack.add_item("hp_potion", 5)
	var equipment = load("res://ui/equipment.gd").new(backpack)
	var player_status = load("res://ui/player_status.gd").new()
	var skillbar = load("res://ui/skillbar.gd").new()
	var skills_db = load("res://ui/skills_db.gd").new()
	var skill_progress = load("res://ui/skill_progress.gd").new(skills_db)
	for id in ["fireball", "iceSpike", "lightningStrike", "blizzard"]:
		if skills_db.has_skill(id):
			var def: Dictionary = skills_db.get_def(id).duplicate(true)
			var eff: Dictionary = skills_db.effect(id, player_status.level)
			def["cooldown_s"] = eff.cooldown_s
			def["mp_cost"] = eff.mp_cost
			def["tier"] = 1
			def["two_stage"] = id in ["fireball", "iceSpike"]
			skillbar.skills[id] = def
	skillbar.assign(0, "fireball")
	skillbar.assign(1, "iceSpike")
	skillbar.assign(2, "lightningStrike")
	skillbar.assign(3, "blizzard")
	var sbar = load("res://ui/status_bar.gd").new()
	root.add_child(sbar)
	sbar.set_hp(76, 300)
	sbar.set_mp(48, 120)
	sbar.set_ammo(30, 90)
	sbar.set_weapon_name("AK-74")
	sbar.set_kills(3)
	var bph = load("res://ui/backpack_hud.gd").new()
	bph.name = "BackpackHud"
	sbar.add_child(bph)
	bph.setup(backpack, equipment, player_status, skillbar)
	var sp: Node = bph.find_child("SkillPage", true, false)
	if sp != null and sp.has_method("set_progress"):
		sp.set_progress(skill_progress)
		sp.set_db(skills_db)
