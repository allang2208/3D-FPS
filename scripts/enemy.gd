extends CharacterBody3D
## 通用敌人：追击玩家 / 远处游荡 / 受击闪红 / 接触伤害 / 死亡倒地重生
## 子节点约定：Collision（CollisionShape3D）+ Model（GLB 或代码拼装，名字以 Leg 开头的子节点会摆动）

@export var max_hp := 50
@export var chase_speed := 3.0
@export var wander_speed := 1.2
@export var contact_damage := 10
@export var attack_cd := 0.8
@export var model_offset_y := 0.0
@export var walk_bob_amp := 0.03
@export var walk_bob_speed := 14.0

const CHASE_DIST := 14.0
const RESPAWN_TIME := 3.0

var _player: Node3D
var _kill_cb: Callable
var _model: Node3D
var _rig: Node3D  # 带骨骼动画的模型（有 rig_update 方法，如黑狼 WolfRig）
var _rig_t := 0.0
var _mat: StandardMaterial3D
var _legs: Array[Node3D] = []
var _hp: int
var _dead := false
var _dead_t := 0.0
var _walk_t := 0.0
var _moving := false
var _flash_t := 0.0
var _lunge_t := 0.0
var _attack_t := 0.0
var _wander_target := Vector3.ZERO
var _wander_timer := 0.0

func setup(player: Node3D, kill_cb: Callable) -> void:
	_player = player
	_kill_cb = kill_cb
	_hp = max_hp

func _ready() -> void:
	collision_layer = 2
	collision_mask = 5  # 1 墙体 + 4 玩家
	for child in get_children():
		if child is Node3D and child.name != "Collision":
			_model = child
			_find_material(child)
			for c in child.get_children():
				if c.name.begins_with("Leg"):
					_legs.append(c)
	_wander_target = global_position
	if _model != null and _model.has_method("rig_update"):
		_rig = _model

func _find_material(n: Node) -> void:
	if n is MeshInstance3D and n.mesh and n.mesh.get_surface_count() > 0:
		var m := n.get_active_material(0) as StandardMaterial3D
		if m:
			_mat = m
	for c in n.get_children():
		_find_material(c)

func take_damage(d: int) -> bool:
	if _dead:
		return false
	_hp -= d
	_flash_t = 0.12
	if _hp <= 0:
		_die()
		return true
	return false

func _die() -> void:
	_dead = true
	_dead_t = 0.0
	collision_layer = 0
	if _kill_cb.is_valid():
		_kill_cb.call()

func _physics_process(delta: float) -> void:
	_flash_t = maxf(0.0, _flash_t - delta)
	if _mat:
		if _flash_t > 0.0:
			_mat.emission_enabled = true
			_mat.emission = Color(1.0, 0.25, 0.2)
		else:
			_mat.emission_enabled = false
	if _dead:
		_dead_t += delta
		if _model:
			_model.rotation.x = minf(PI / 2, _model.rotation.x + delta * 2.5)
			_model.position.y = maxf(0.0, _model.position.y - delta * 0.4)
		if _rig:
			_rig.rig_update(_dead_t, false, 0.0, true)
		if _dead_t >= RESPAWN_TIME:
			_respawn()
		return
	if _player == null:
		return
	_lunge_t = maxf(0.0, _lunge_t - delta)
	if _lunge_t > 0.0 and _model and _rig == null:
		_model.rotation.x = 0.3 * (_lunge_t / 0.25)
	_attack_t = maxf(0.0, _attack_t - delta)
	_contact_attack()
	var to_player := _player.global_position - global_position
	var dist := Vector2(to_player.x, to_player.z).length()
	if dist > CHASE_DIST:
		_wander(delta)
	else:
		_chase(delta, to_player, dist)
	_walk_t += delta
	_swing_legs()
	_idle_breath()
	if _rig:
		# 步频随实际移速缩放，减少滑步（约 3.3 rad/s 每 m/s，待机 4.0）
		var spd := Vector2(velocity.x, velocity.z).length()
		_rig_t += delta * (clampf(spd * 3.3, 4.0, 14.0) if _moving else 4.0)
		_rig.rig_update(_rig_t, _moving, _lunge_t, false)

func _contact_attack() -> void:
	if _attack_t > 0.0 or _player == null or not _player.has_method("take_damage"):
		return
	var to_p := _player.global_position - global_position
	if Vector2(to_p.x, to_p.z).length() < 1.4:
		_attack_t = attack_cd
		_lunge_t = 0.25
		_player.take_damage(contact_damage)

func _chase(delta: float, to_player: Vector3, dist: float) -> void:
	_moving = true
	var dir := Vector3(to_player.x, 0, to_player.z)
	if dist > 0.01:
		dir = dir.normalized()
	velocity.x = dir.x * chase_speed
	velocity.z = dir.z * chase_speed
	_turn_to(dir, delta)
	move_and_slide()
	if _model:
		_model.position.y = model_offset_y + absf(sin(_walk_t * walk_bob_speed)) * walk_bob_amp

func _wander(delta: float) -> void:
	_wander_timer -= delta
	if _wander_timer <= 0.0 or global_position.distance_to(_wander_target) < 0.8:
		_wander_timer = 3.0 + randf() * 3.0
		_wander_target = Vector3(randf_range(-11.0, 11.0), 0, randf_range(-11.0, 11.0))
	var to_t := _wander_target - global_position
	var dist := Vector2(to_t.x, to_t.z).length()
	if dist < 0.4:
		_moving = false
		velocity.x = 0
		velocity.z = 0
	else:
		_moving = true
		var dir := Vector3(to_t.x, 0, to_t.z).normalized()
		velocity.x = dir.x * wander_speed
		velocity.z = dir.z * wander_speed
		_turn_to(dir, delta)
		if _model:
			_model.position.y = model_offset_y + absf(sin(_walk_t * walk_bob_speed * 0.6)) * walk_bob_amp * 0.6
	move_and_slide()

func _turn_to(dir: Vector3, delta: float) -> void:
	var yaw := atan2(dir.x, dir.z)
	rotation.y = lerp_angle(rotation.y, yaw, 8.0 * delta)

func _swing_legs() -> void:
	if _legs.is_empty():
		return
	var amp := 0.4 if _moving else 0.0
	for i in _legs.size():
		_legs[i].rotation.x = sin(_walk_t * walk_bob_speed * 0.7 + float(i) * PI) * amp * 0.4

func _idle_breath() -> void:
	if _moving or _model == null:
		return
	_model.position.y = model_offset_y + sin(_walk_t * 2.2) * 0.02

func _respawn() -> void:
	_hp = max_hp
	_dead = false
	_dead_t = 0.0
	_moving = false
	collision_layer = 2
	velocity = Vector3.ZERO
	global_position = Vector3(randf_range(-11.0, 11.0), 0, randf_range(-11.0, 11.0))
	_rig_t = 0.0
	if _rig:
		_rig.rig_reset()
	if _model:
		_model.rotation.x = 0.0
		_model.position.y = model_offset_y
		for l in _legs:
			l.rotation.x = 0.0
