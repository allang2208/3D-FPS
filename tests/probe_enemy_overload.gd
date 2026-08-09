extends SceneTree
## enemy.gd 过载验证：apply_electrified 叠满 5 层 → 眩晕 1.2s + 150px 传导电击
var _e1: Node3D
var _e2: Node3D
var _t := 0
var _stage := 0

func _process(_delta: float) -> bool:
	if _t == 0:
		_e1 = load("res://scripts/enemy.gd").new()
		_e1.name = "OverloadEnemy"
		root.add_child(_e1)
		_e1.global_position = Vector3(0, 0.5, 0)
		_e2 = load("res://tests/probe_skill_enemy.gd").new()
		_e2.name = "NearEnemy"
		root.add_child(_e2)
		_e2.global_position = Vector3(0, 0.5, -1.5)
		_e1.apply_electrified(5, 4000, 10, 10)
		print("OVERLOAD applied")
		_stage = 1
		_t = 1
	elif _stage == 1 and _t == 5:
		var b: RefCounted = _e1.get("_buffs")
		print("OVERLOAD e1_stun=", b.has("stun"), " stun_remaining=", snappedf(b.remaining("stun"), 0.01),
			" e1_elect=", b.stacks("electrified"))
		print("OVERLOAD e2_hp=", _e2.get("_hp"), " (expect 56 = 100 - 44)")
		quit(0)
		return false
	_t += 1
	return false
