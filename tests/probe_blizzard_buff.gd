extends SceneTree
## 端到端验证：暴风雪 cast → 区域内敌人叠寒冷（buff_system 生效）
var _cam: Camera3D
var _caster: Node3D
var _e1: Node3D
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
		_caster.global_position = Vector3(0, 0, 0)
		_e1 = load("res://scripts/enemy.gd").new()
		_e1.name = "BlizzardEnemy"
		root.add_child(_e1)
		_e1.global_position = Vector3(0, 0.5, -6)
		_e1.setup(null, Callable())
		var db = load("res://ui/skills_db.gd").new()
		var eff = db.effect_raw("blizzard", 1)
		load("res://scripts/area_skill.gd").cast(root, _caster, 1, 10, 10, "blizzard", eff)
		print("BLIZZARD cast")
		_stage = 1
		_t = 1
	elif _stage == 1 and _t == 150:
		var b: RefCounted = _e1.get("_buffs")
		print("BLIZZARD chill_stacks=", b.stacks("chill"), " speed_mul=", snappedf(b.speed_mul(), 0.001))
		var ok: bool = b.stacks("chill") >= 2 and b.speed_mul() < 0.98
		print("BLIZZARD_RESULT ", "PASS" if ok else "FAIL")
		quit(0)
		return false
	_t += 1
	return false
