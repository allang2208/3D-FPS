extends SceneTree
## UI 面板实拍：装备页 / 属性页 / 物品浮窗
## 运行：$godot --rendering-driver opengl3 --path 'E:\3d\3-dfps' --script res://tests/render_ui_panels.gd

var _frames := 0
var _hud: Control
var _bp
var _eq
var _st


func _initialize() -> void:
	var item_db = load("res://ui/item_db.gd").new()
	_bp = load("res://ui/backpack.gd").new(item_db)
	_bp.add_item("hp_potion", 5)
	_bp.add_item("mp_potion", 3)
	_bp.add_item("rusty_sword", 1)
	_bp.add_item("g18_pistol", 1)
	_bp.add_item("small_shield", 1)
	_bp.add_item("lunar_helmet", 1)
	_bp.add_item("ring_oracle", 1)
	_bp.add_item("hp_potion", 5)

	_eq = load("res://ui/equipment.gd").new(_bp)
	for i in _bp.slots.size():
		if _bp.slots[i] != null and String(_bp.slots[i].get("id", "")) == "rusty_sword":
			_eq.equip_from_backpack(i)
			break

	_st = load("res://ui/player_status.gd").new()
	_st.hp = 76
	_st.mp = 48
	_st.stamina = 62
	_st.exp = 42
	_st.level = 3


func _process(_delta: float) -> bool:
	_frames += 1
	if _frames == 1:
		var sb = load("res://ui/skillbar.gd").new()
		var skills_db = load("res://ui/skills_db.gd").new()
		var sb_skills := {}
		if skills_db.has_skill("fireball"):
			var fb: Dictionary = skills_db.get_def("fireball").duplicate(true)
			var eff: Dictionary = skills_db.effect("fireball", _st.level)
			fb["cooldown_s"] = eff.cooldown_s
			fb["mp_cost"] = eff.mp_cost
			fb["tier"] = 1
			fb["two_stage"] = true
			sb_skills["fireball"] = fb
		sb.setup(sb_skills)
		sb.assign(0, "fireball")

		var ui_root := Control.new()
		ui_root.set_anchors_preset(Control.PRESET_FULL_RECT)
		root.add_child(ui_root)
		var bg := ColorRect.new()
		bg.color = Color(0.10, 0.10, 0.11)
		bg.set_anchors_preset(Control.PRESET_FULL_RECT)
		ui_root.add_child(bg)

		_hud = load("res://ui/backpack_hud.gd").new()
		ui_root.add_child(_hud)
		_hud.setup(_bp, _eq, _st, sb)
		_hud.set_panel_open(true)
		_hud.set_tab("equip")
	match _frames:
		24:
			_save("res://docs/preview/ui_panel_equip.png")
			_hud.set_tab("status")
		36:
			_save("res://docs/preview/ui_panel_status.png")
			_hud.show_item_tooltip({"id": "rusty_sword", "count": 1}, Vector2(360, 300))
		46:
			_save("res://docs/preview/ui_panel_tooltip.png")
			quit(0)
			return true
	return false


func _save(path: String) -> void:
	var img := root.get_viewport().get_texture().get_image()
	if img != null and img.get_width() > 0:
		img.save_png(path)
		print("SAVED ", ProjectSettings.globalize_path(path))
