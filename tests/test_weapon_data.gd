extends SceneTree
## 无头验证：武器数据配置化（GunData → WeaponData Resource）
## 1) 默认 AKM 数据生效（弹匣 30 / 备弹 90 / 伤害 25 / 射速 0.13 / 后坐力 pattern 9 发）
## 2) 运行时换 WeaponData → 弹匣容量/伤害/射速随之改变（多武器架构）
## 运行：& $godot --headless --path 'E:\3d\3-dfps' --script res://tests/test_weapon_data.gd

var _gun: Node
var _ok_default := false
var _ok_custom := false
var _ok_shot_signal := false
var _stage := 0
var _stage_start := 0

func _initialize() -> void:
	var scene: PackedScene = load("res://scenes/main.tscn")
	root.add_child(scene.instantiate())

func _process(_delta: float) -> bool:
	if _gun == null:
		_gun = root.get_node_or_null("Main/Player/Camera3D/Gun")
		if _gun == null:
			return false
		# 测试期间不被敌人干扰
		var player: Node = root.get_node_or_null("Main/Player")
		if player:
			player.set("hp", 99999)
		var data: Resource = _gun.get("data")
		_ok_default = data != null \
			and data.get("weapon_name") == "AK-74" \
			and int(data.get("mag_size")) == 30 \
			and int(data.get("reserve")) == 90 \
			and int(data.get("damage")) == 25 \
			and absf(float(data.get("fire_interval")) - 0.13) < 0.001 \
			and data.get("recoil_pattern").size() == 9 \
			and int(_gun.get("ammo")) == 30 \
			and int(_gun.get("reserve")) == 90
		print("TEST akm_data=", _ok_default)
		_stage = 1
		_stage_start = Time.get_ticks_msec()
		# 换"冲锋手枪"：弹匣 12 / 备弹 36 / 伤害 18 / 射速 0.08
		var wd: Resource = load("res://scripts/weapon_data.gd").new()
		wd.set("weapon_name", "PDW")
		wd.set("mag_size", 12)
		wd.set("reserve", 36)
		wd.set("damage", 18)
		wd.set("fire_interval", 0.08)
		_gun.set("data", wd)
		_gun.set("ammo", 5)
		_gun.set("reserve", 36)
		_gun.reloaded.connect(func(_a: int, _r: int) -> void: _ok_shot_signal = _a == 12)
		_gun.call("_start_reload")
		return false
	var now := Time.get_ticks_msec()
	if _stage == 1 and now - _stage_start > 2500:
		var ammo: int = int(_gun.get("ammo"))
		var data: Resource = _gun.get("data")
		_ok_custom = ammo == 12 and int(data.get("mag_size")) == 12 and _ok_shot_signal
		print("TEST custom_weapon ammo=", ammo, " expected=12 ok=", _ok_custom)
		quit(0 if _ok_default and _ok_custom else 1)
		return false
	return false
