extends SceneTree
## 无头验证技能栏数据层移植：绑定唯一性/换位、冷却、法杖门槛、长按标记、特殊攻击槽
## 运行：$godot --headless --path 'E:\3d\3-dfps' --script res://tests/test_skillbar.gd

const SkillBarScript := preload("res://ui/skillbar.gd")

const FAKE_SKILLS := {
	"iceSpike": {"name": "冰锥", "icon": "res://assets/ui/icons/equip/1-rusty_sword_macro.png", "cooldown_s": 3.0, "tier": 1},
	"iceWall": {"name": "冰墙", "icon": "res://assets/ui/icons/equip/1-rusty_sword_macro.png", "cooldown_s": 8.0, "tier": 2},
	"droneSkill": {"name": "无人机", "icon": "res://assets/ui/icons/equip/1-rusty_sword_macro.png", "cooldown_s": 15.0, "tier": 1, "hold": true},
	"fireball": {"name": "火球", "icon": "res://assets/ui/icons/equip/1-rusty_sword_macro.png", "cooldown_s": 2.0, "tier": 1},
}

var _fail := 0
var _stage := 0
var _stage_start := 0
var _hud: Node

func _check(name: String, ok: bool) -> void:
	print("TEST ", name, "=", ok)
	if not ok:
		_fail += 1

func _initialize() -> void:
	_data_tests()
	var scene: PackedScene = load("res://scenes/main.tscn")
	var main: Node = scene.instantiate()
	root.add_child(main)
	current_scene = main

func _process(_delta: float) -> bool:
	if _stage == 0:
		_stage = 1
		_hud = root.get_node_or_null("Main/StatusBar/BackpackHud")
		_check("skillbar_wired", _hud != null and _hud.get("skillbar") != null)
		if _hud == null or _hud.get("skillbar") == null:
			quit(1)
			return false
		var sb = _hud.get("skillbar")
		sb.setup(FAKE_SKILLS)
		sb.assign(0, "iceSpike")
		_check("skill_slot_refresh", _hud.get("_skill_slots")[0].get_node("Content/Icon").texture != null)
		# 触发 → 冷却遮罩出现
		sb.trigger(0)
		_check("skill_cd_overlay", bool(_hud.get("_skill_slots")[0].get_node("Content/CD").visible))
		# 再次触发被冷却拦截
		var r2 = sb.trigger(0)
		_check("skill_cd_block", not bool(r2.get("ok", false)) and String(r2.get("reason", "")).contains("冷却"))
		# 法杖门槛灰化：冰墙(tier2) 未装备法杖 → 不可用
		sb.assign(1, "iceWall")
		var req = sb.ready_check(1)
		_check("skill_staff_gate", not bool(req.get("ok", false)) and String(req.get("reason", "")).contains("法杖"))
		_check("skill_dim_visual", bool(_hud.get("_skill_slots")[1].get_node("Content/Dim").visible))
		sb.set_staff_equipped(true)
		_check("skill_staff_ok", bool(sb.ready_check(1).get("ok", false)))
		_check("skill_dim_cleared", not bool(_hud.get("_skill_slots")[1].get_node("Content/Dim").visible))
		# 冷却到期后可用
		sb.tick(8100.0)
		_check("skill_cd_expire", bool(sb.ready_check(0).get("ok", false)))
		_stage = 2
		_stage_start = Time.get_ticks_msec()
	elif _stage == 2 and Time.get_ticks_msec() - _stage_start > 300:
		quit(0 if _fail == 0 else 1)
	return false

func _data_tests() -> void:
	var sb := SkillBarScript.new()
	sb.setup(FAKE_SKILLS)
	_check("assign_ok", sb.assign(0, "iceSpike") and sb.resolve(0) == "iceSpike")
	# 唯一性：同技能绑到别的槽 → 原槽被清空
	sb.assign(2, "iceSpike")
	_check("assign_unique_moves", sb.resolve(0) == "" and sb.resolve(2) == "iceSpike")
	# 换位（目标槽有内容 → 内容挪到源槽）
	sb.assign(0, "fireball")
	sb.assign(2, "fireball")
	_check("assign_swap", sb.resolve(0) == "iceSpike" and sb.resolve(2) == "fireball")
	# swap / unassign
	sb.swap(0, 1)
	_check("swap_works", sb.resolve(0) == "" and sb.resolve(1) == "iceSpike")
	sb.unassign(1)
	_check("unassign_works", sb.resolve(1) == "")
	_check("reject_unknown", not sb.assign(0, "nope"))
	# 长按标记
	_check("hold_flag", sb.is_hold("droneSkill") and not sb.is_hold("fireball"))
	# 特殊攻击槽（夜与火之剑）
	sb.refresh_special({"specialAttackType": "nightFlame"})
	_check("special_enabled", sb.special_ready())
	sb.set_special_cooldown(5000.0)
	_check("special_cd", not sb.special_ready())
	sb.refresh_special({})
	_check("special_disabled", not sb.special_ready())
