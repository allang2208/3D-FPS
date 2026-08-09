extends SceneTree
## 无头冒烟：Hitbox 部位伤害（狼头 ×2 / 躯干 ×1）+ 弹道后坐力 pattern 停火回退
## 运行：$godot --headless --path 'E:\3d\3-dfps' --script res://tests/test_hitbox.gd

const ProjectileScript := preload("res://scripts/projectile.gd")

var _frames := 0
var _main: Node
var _wolf: Node3D
var _player: Node3D
var _gun: Node
var _head_dir := Vector3(0, 0, 1)
var _head_origin := Vector3.ZERO
var _mult_ok := false

func _initialize() -> void:
	var scene: PackedScene = load("res://scenes/main.tscn")
	_main = scene.instantiate()
	root.add_child(_main)

func _process(_delta: float) -> bool:
	_frames += 1
	if _frames == 1:
		_wolf = _main.get_node_or_null("WolfEnemy") as Node3D
		_player = _main.get_node_or_null("Player") as Node3D
		_gun = root.get_node_or_null("Main/Player/Camera3D/Gun")
		if _wolf == null or _player == null or _gun == null:
			push_error("缺少狼/玩家/枪")
			quit(1)
			return false
		_wolf.global_position = Vector3(0, 0, 0)
		_player.global_position = Vector3(0, 0.2, 8)
		_player.set("hp", 99999)
		var hb := _wolf.get_node_or_null("HitboxHead") as CollisionShape3D
		if hb == null:
			push_error("狼没有生成 HitboxHead")
			quit(1)
			return false
		var head := hb.global_position
		print("TEST head=", head, " shape_multipliers=", _wolf.get("_shape_multipliers"))
		# 头部命中球必须伸出躯干碰撞胶囊（radius 0.55），否则外部射线先打躯干
		if head.length() <= 0.33:
			push_error("头部 hitbox 没有伸出碰撞胶囊，爆头不可达: " + str(head.length()))
			quit(1)
			return false
		var h_dir := head - _wolf.global_position
		h_dir.y = 0.0
		if h_dir.length() < 0.05:
			h_dir = Vector3(0, 0, 1)
		_head_dir = h_dir.normalized()
		_head_origin = head + _head_dir * 1.5
		# 单位检查：shape 0（躯干）=1.0，shape 1（头）=2.0
		_mult_ok = _wolf.get_shape_multiplier(0) == 1.0 and _wolf.get_shape_multiplier(1) == 2.0
		print("TEST shape_multiplier_unit=", _mult_ok)
	if _frames == 2:
		# 头部：25 × 2 = 50 → 85 - 50 = 35
		ProjectileScript.fire(root, _head_origin, -_head_dir, 90.0, 25, 0.0)
	if _frames == 4:
		# 躯干：25 × 1 = 25 → 35 - 25 = 10
		ProjectileScript.fire(root, Vector3(0, 0.5, -2.5), Vector3(0, 0, 1), 90.0, 25, 0.0)
	if _frames == 40:
		var hp: int = int(_wolf.get("_hp"))
		var dmg_ok: bool = hp == 85 - 50 - 25
		print("TEST hp=", hp, " expected=", 85 - 50 - 25, " ok=", dmg_ok)
		# 弹道 pattern 停火回退：3 发 → 停 1s（延迟 0.3 + 每 0.05 回退 1 发）→ 0
		_gun.set("_pattern_idx", 3)
		_gun.set("_last_fire_t", (Time.get_ticks_msec() * 0.001) - 1.0)
		_gun.call("_update_recoil_recovery", 0.0)
		var idx: int = int(_gun.get("_pattern_idx"))
		print("TEST recoil_recovery idx=", idx, " ok=", idx == 0)
		quit(0 if (dmg_ok and _mult_ok and idx == 0) else 1)
		return false
	return false
