extends SceneTree
## Buff 系统验证（旧版 damageable-entity 状态机制移植）：
## 寒冷叠层→冻结、灼烧 DoT、感电/魔力易伤/无人机易伤修正、中毒/流血/续疗、免疫、激励、恐惧
var _e1: Node3D
var _caster: Node3D
var _fail := 0
var _t := 0
var _stage := 0

func _check(label: String, got, want) -> void:
	if got != want:
		_fail += 1
		print("FAIL ", label, " got=", got, " want=", want)
	else:
		print("OK   ", label, " = ", got)

func _process(_delta: float) -> bool:
	if _t == 0:
		_caster = Node3D.new()
		_caster.set("_matk", 100)
		_caster.set("_intt", 50)
		root.add_child(_caster)
		_e1 = load("res://scripts/enemy.gd").new()
		_e1.name = "BuffEnemy"
		root.add_child(_e1)
		_e1.setup(null, Callable())
		_e1.max_hp = 10000
		_e1._hp = 10000
		_stage = 1
		_t = 1
	elif _stage == 1:
		_run_tests()
		print("BUFF_RESULT fails=", _fail)
		quit(0)
		return false
	_t += 1
	return false

func _run_tests() -> void:
	var b: RefCounted = _e1.get("_buffs")
	# 寒冷叠层 + 移速倍率
	_e1.apply_chill(5, 2500, 0.05)
	_check("chill_speed_mul", snappedf(b.speed_mul(), 0.001), 0.75)
	# 20 层触发冻结（扣 10 层）
	_e1.apply_chill(15, 2500, 0.05)
	_check("chill_freeze", b.has("frozen"), true)
	_check("chill_after_freeze", b.stacks("chill"), 10)
	_check("frozen_lock", b.is_control_locked(), true)
	_check("frozen_phys_bonus", snappedf(b.incoming_damage_mul("physical"), 0.001), 1.5)
	# 冻结下不再叠寒冷
	_e1.apply_chill(3, 2500, 0.05)
	_check("chill_blocked_by_frozen", b.stacks("chill"), 10)
	b.clear()
	# 眩晕
	_e1.apply_stun(500)
	_check("stun_lock", b.is_control_locked(), true)
	b.clear()
	# 感电：+3%/层
	_e1.apply_electrified(2, 4000, 10, 10)
	_check("electrified_stacks", b.stacks("electrified"), 2)
	_check("electrified_bonus", snappedf(b.incoming_damage_mul("electric"), 0.001), 1.06)
	_check("take_damage_electric", _dmg_with("electric"), 106)
	b.clear()
	# 魔力易伤 +5%/层
	_e1.apply_magic_vulnerability(1, 5000)
	_check("magic_vuln", snappedf(b.incoming_damage_mul("magic"), 0.001), 1.05)
	b.clear()
	# 无人机易伤 +10%/层（全类型）
	_e1.apply_drone_vulnerability(2, 15000)
	_check("drone_vuln", snappedf(b.incoming_damage_mul("physical"), 0.001), 1.2)
	b.clear()
	# 灼烧 DoT：3 层 × floor(100×0.5) = 150 / 0.5s
	var hp_before: int = int(_e1._hp)
	_e1.apply_burn(_caster, 3, 3500, 0.5, 100)
	_check("burn_stacks", b.stacks("burn"), 3)
	b.tick(0.5, _e1)
	_check("burn_dot", hp_before - _e1._hp, 150)
	b.clear()
	# 中毒 DoT：每秒层数点
	hp_before = int(_e1._hp)
	_e1.apply_poison(3)
	b.tick(1.0, _e1)
	_check("poison_dot", hp_before - _e1._hp, 3)
	b.clear()
	# 流血 DoT：每层每秒当前生命 1%
	hp_before = int(_e1._hp)
	_e1.apply_bleed(2)
	b.tick(1.0, _e1)
	_check("bleed_dot", hp_before - _e1._hp, maxi(1, floori(hp_before * 0.01)))
	b.clear()
	# 圣光续疗 HoT：每秒 1%×层数 最大生命
	var hp_after: int = int(_e1._hp)
	_e1.apply_holy_renewal(2, 3000)
	b.tick(1.0, _e1)
	_check("renewal_hot", _e1._hp - hp_after, 200)
	b.clear()
	# 状态免疫：不再入库其他状态
	_e1.apply_status_immune(5000)
	_e1.apply_chill(1, 1000, 0.05)
	_check("immune_blocks", b.has("chill"), false)
	b.clear()
	# 激励：移速 ×1.33、物攻 ×1.5
	_e1.apply_inspire(5000, 1.33, 1.5)
	_check("inspire_atk", snappedf(b.atk_mul(), 0.001), 1.5)
	_check("inspire_speed", snappedf(b.speed_mul(), 0.001), 1.33)
	# 恐惧：每层移速再降 33%
	_e1.apply_fear(3000)
	_check("fear_speed", snappedf(b.speed_mul(), 0.001), snappedf(1.33 * 0.67, 0.001))
	b.clear()
	# 到期移除
	_e1.apply_stun(100)
	b.tick(0.2, _e1)
	_check("stun_expire", b.has("stun"), false)
	# 快照（HUD 数据源）
	_e1.apply_stun(500)
	var snap: Array = b.effect_snapshot()
	_check("snapshot_size", snap.size() > 0, true)
	_check("snapshot_keys", snap[0].has("icon") and snap[0].has("desc") and snap[0].has("color"), true)

func _dmg_with(damage_type: String) -> int:
	var hp0: int = int(_e1._hp)
	_e1.take_damage(100, damage_type, _caster)
	return hp0 - _e1._hp
