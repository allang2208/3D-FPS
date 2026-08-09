extends SceneTree
## 无头验证火球技能迁徙：skills_db 公式、skillbar 触发/MP/冷却、场景 Q 键发射
## 运行：$godot --headless --path 'E:\3d\3-dfps' --script res://tests/test_fireball.gd

const SkillsDbScript := preload("res://ui/skills_db.gd")
const SkillBarScript := preload("res://ui/skillbar.gd")

var _fail := 0
var _stage := 0
var _stage_start := 0
var _main: Node
var _hud: Node

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
		_hud = _main.get_node_or_null("StatusBar/BackpackHud")
		_check("fireball_bound", _hud != null and String(_hud.get("skillbar").resolve(0)) == "fireball")
		if _hud == null:
			quit(1)
			return false
		# 按 Q → 技能触发 → 生成火球 + MP 扣除
		var ev := InputEventKey.new()
		ev.keycode = KEY_Q
		ev.physical_keycode = KEY_Q
		ev.pressed = true
		Input.parse_input_event(ev)
		_stage = 2
		_stage_start = Time.get_ticks_msec()
	elif _stage == 2 and Time.get_ticks_msec() - _stage_start > 400:
		var sb = _hud.get("skillbar")
		var st = _hud.get("_player_status")
		var fb_found := false
		for c in _main.get_children():
			if c != null and c.get_script() != null and String(c.get_script().resource_path).ends_with("fireball.gd"):
				fb_found = true
				_check("fireball_damage", int(c.get("_damage")) == 172)
		_check("fireball_spawned", fb_found)
		_check("fireball_mp_cost", int(st.get("mp")) == 50)
		_check("fireball_cooldown", sb.get_cooldown("fireball") > 0.0)
		quit(0 if _fail == 0 else 1)
	return false

func _data_tests() -> void:
	var db := SkillsDbScript.new()
	_check("db_has_fireball", db.has_skill("fireball"))
	var eff: Dictionary = db.effect("fireball", 1)
	_check("effect_damage_base", is_equal_approx(eff.damage_base, 90.0))
	_check("effect_magic_mul", is_equal_approx(eff.magic_mul, 2.5))
	_check("effect_int_mul", is_equal_approx(eff.int_mul, 3.25))
	_check("effect_cooldown", is_equal_approx(eff.cooldown_s, 20.0))
	_check("effect_mp", int(eff.mp_cost) == 50)
	_check("effect_radius", is_equal_approx(eff.explosion_radius_m, 1.19))
	_check("effect_speed", is_equal_approx(eff.fly_speed_m, 22.4))
	_check("effect_range", is_equal_approx(eff.max_range_m, 16.8))
	# skillbar：绑定/触发/MP/冷却
	var sb := SkillBarScript.new()
	var def: Dictionary = db.get_def("fireball").duplicate(true)
	def["cooldown_s"] = eff.cooldown_s
	def["mp_cost"] = eff.mp_cost
	def["tier"] = 1
	sb.setup({"fireball": def})
	_check("sb_assign", sb.assign(0, "fireball"))
	var status = load("res://ui/player_status.gd").new()
	_check("sb_trigger_ok", bool(sb.trigger(0, status).get("ok", false)))
	_check("sb_mp_deduct", status.mp == 50)
	_check("sb_cd_set", sb.get_cooldown("fireball") > 0.0)
	_check("sb_cd_block", not bool(sb.trigger(0, status).get("ok", false)))
	status.set_mp(10)
	sb.tick(30000.0)
	_check("sb_mp_insufficient", not bool(sb.trigger(0, status).get("ok", false)) \
		and String(sb.trigger(0, status).get("reason", "")).contains("魔法不足"))
