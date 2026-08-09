extends SceneTree
## 雷暴领域验证：落雷主目标 + 传导（strike 伤害公式）

var _cam: Camera3D
var _caster: Node3D
var _e1: Node3D
var _e2: Node3D
var _t := 0
var _stage := 0

func _process(_delta: float) -> bool:
	if _t == 0:
		_cam = Camera3D.new()
		_cam.current = true
		_caster = Node3D.new()
		_caster.name = "Player"
		_caster.add_child(_cam)
		root.add_child(_caster)
		_e1 = load("res://tests/probe_skill_enemy.gd").new()
		_e1.name = "Enemy1"
		root.add_child(_e1)
		_e1.global_position = Vector3(0, 0.5, -3.0)
		_e2 = load("res://tests/probe_skill_enemy.gd").new()
		_e2.name = "Enemy2"
		root.add_child(_e2)
		_e2.global_position = Vector3(0, 0.5, -4.6)  # 传导距离 1.6m ≤ chainRange(160px=2.24m)
		var db = load("res://ui/skills_db.gd").new()
		var eff = db.effect_raw("stormDomain", 1)
		load("res://scripts/area_skill.gd").cast(root, _caster, 1, 10, 10, "stormDomain", eff)
		print("STORM cast")
		_stage = 1
		_t = 1
	elif _stage == 1 and _t == 140:
		var sk: Node3D = null
		for c in root.get_children():
			if c != null and c.get_script() != null and String(c.get_script().resource_path).ends_with("area_skill.gd"):
				sk = c
				break
		print("STORM node=", sk, " hits=", sk.get("_hits") if sk != null else "-",
			" eff_interval=", sk.get("_eff").get("strikeIntervalMs") if sk != null else "-")
		if sk != null:
			print("STORM children=", sk.get_child_count(), " cloud=", sk.get_node_or_null("StormCloud"))
			for ch in sk.get_children():
				print("  child=", ch.name, " pos=", ch.global_position if ch is Node3D else "")
		print("STORM e1_hp=", _e1.get("_hp"), " stun=", _e1.get("_stun_ms"), " elect=", _e1.get("_electrified_stacks"),
			" e2_hp=", _e2.get("_hp"), " stun=", _e2.get("_stun_ms"), " elect=", _e2.get("_electrified_stacks"))
		quit(0)
		return false
	_t += 1
	return false
