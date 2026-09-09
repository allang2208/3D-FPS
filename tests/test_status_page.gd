extends SceneTree
## 无头验证属性栏迁移：旧版公式（六维/战斗属性/上限）+ 状态页签 + hp/击杀同步
## 运行：$godot --headless --path 'E:\3d\3-dfps' --script res://tests/test_status_page.gd

const PlayerStatusScript := preload("res://ui/player_status.gd")

var _fail := 0
var _stage := 0
var _stage_start := 0
var _main: Node
var _hud: Node
var _player: Node

func _check(name: String, ok: bool) -> void:
	print("TEST ", name, "=", ok)
	if not ok:
		_fail += 1

func _initialize() -> void:
	_data_tests()
	var scene: PackedScene = load("res://scenes/main.tscn")
	_main = scene.instantiate()
	root.add_child(_main)
	current_scene = _main

func _process(_delta: float) -> bool:
	if _stage == 0:
		_stage = 1
		var hud_host := root.get_node_or_null("HUD")
		if hud_host != null:
			hud_host._ensure_built()
			_hud = hud_host.backpack_hud
		if _hud == null:
			_hud = _main.find_child("BackpackHud", true, false)
		_player = _main.get_node_or_null("Player")
		_check("status_wired", _hud != null and _hud.get("_status_page") != null)
		if _hud == null or _hud.get("_status_page") == null:
			quit(1)
			return false
		_player.set("hp", 100000)
		var st = _hud.get("_status_page").get("status")
		_check("status_default_tab", String(_hud.get("_current_tab")) == "equip" \
			and not bool(_hud.get("_status_page").visible))
		_check("status_row_atk", String(_hud.get("_status_page").get("_rows")["atk"].text) == str(st.atk()))
		_check("status_row_hp", String(_hud.get("_status_page").get("_rows")["kills"].text) == "0")
		# 切页签
		_hud.set_tab("status")
		_check("status_tab_switch", String(_hud.get("_current_tab")) == "status" \
			and bool(_hud.get("_status_page").visible) \
			and not bool(_hud.get("_equip_page").visible) \
			and String(_hud.get("_panel_title").text).contains("角色状态"))
		_hud.set_tab("equip")
		# 悬停公式浮窗
		var page = _hud.get("_status_page")
		page._show_tooltip("str", Vector2(120, 120))
		_check("status_tooltip", bool(page.get("_tooltip").visible) \
			and String(page.get("_tooltip_title").text) == "力量")
		var strength_card: Control = page.get("_rows")["str"].get_parent().get_parent()
		_check("status_rows_keyboard_focusable", strength_card.focus_mode == Control.FOCUS_ALL)
		strength_card.grab_focus()
		_check("status_focus_opens_tooltip", bool(page.get("_tooltip").visible) \
			and String(page.get("_tooltip_title").text) == "力量")
		strength_card.release_focus()
		page.hide_tooltip()
		_check("status_tooltip_hide", not bool(page.get("_tooltip").visible))
		# hp / 击杀同步
		_player.set("hp", 100)
		_player.take_damage(30)
		_check("status_hp_sync", int(st.get("hp")) == 70)
		var wolf: Node3D = _main.get_node_or_null("WolfEnemy") as Node3D
		if wolf != null:
			wolf.take_damage(9999)
		_stage = 2
		_stage_start = Time.get_ticks_msec()
	elif _stage == 2 and Time.get_ticks_msec() - _stage_start > 300:
		var st = _hud.get("_status_page").get("status")
		_check("status_kills_sync", int(st.get("kills")) >= 1)
		quit(0 if _fail == 0 else 1)
	return false

func _data_tests() -> void:
	var st := PlayerStatusScript.new()
	_check("attrs_default", st.str == 10 and st.dex == 10 and st.intt == 10 \
		and st.con == 10 and st.wis == 10 and st.luck == 10)
	_check("max_hp_formula", st.max_hp() == 200)
	_check("max_mp_formula", st.max_mp() == 250)
	_check("max_stamina", st.max_stamina() == 100)
	_check("max_exp_lv1", st.max_exp() == 416)
	_check("atk_formula", st.atk() == 12)
	_check("def_formula", st.def() == 15)
	_check("matk_formula", st.matk() == 20)
	_check("mdef_formula", st.mdef() == 15)
	_check("crit_formula", st.crit() == 12)
	_check("crit_res_formula", st.crit_res() == 10)
	_check("aspd_formula", is_equal_approx(st.aspd(), 1.2))
	_check("stamina_regen_formula", is_equal_approx(st.stamina_regen(), 1.1))
	var changes := [0]
	st.changed.connect(func() -> void: changes[0] += 1)
	st.set_hp(50)
	st.set_kills(3)
	_check("sync_emits", changes[0] >= 2 and st.hp == 50 and st.kills == 3)
