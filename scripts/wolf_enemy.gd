extends CharacterBody3D
## 黑狼敌人：追击玩家 / 远处游荡 / 受击扣血闪红 / 死亡倒地后重生

@export var max_hp := 85
@export var chase_speed := 3.5
@export var wander_speed := 1.4

const WALK_BOB_AMP := 0.05
const WALK_BOB_SPEED := 14.0

var _player: Node3D
var _hp_label: Label
var _model: Node3D
var _mat: StandardMaterial3D
var _hp: int
var _dead := false
var _dead_t := 0.0
var _walk_t := 0.0
var _moving := false
var _flash_t := 0.0
var _wander_target := Vector3.ZERO
var _wander_timer := 0.0

func setup(player: Node3D, hp_label: Label) -> void:
	_player = player
	_hp_label = hp_label
	_hp = max_hp
	_update_label()

func _ready() -> void:
	collision_layer = 2
	collision_mask = 1
	for child in get_children():
		if child is Node3D and child.name != "Collision":
			_model = child
			_find_material(child)
	_wander_target = global_position
	_update_label()

func _find_material(n: Node) -> void:
	if n is MeshInstance3D and n.mesh and n.mesh.get_surface_count() > 0:
		var m := n.get_active_material(0) as StandardMaterial3D
		if m:
			_mat = m
	for c in n.get_children():
		_find_material(c)

func take_damage(d: int) -> void:
	if _dead:
		return
	_hp -= d
	_flash_t = 0.12
	_update_label()
	if _hp <= 0:
		_die()

func _die() -> void:
	_dead = true
	_dead_t = 0.0
	collision_layer = 0
	_update_label("黑狼：已击杀，3 秒后重生")

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
		if _dead_t >= 3.0:
			_respawn()
		return
	if _player == null:
		return
	var to_player := _player.global_position - global_position
	var dist := Vector2(to_player.x, to_player.z).length()
	if dist > 14.0:
		_wander(delta)
	else:
		_chase(delta, to_player, dist)
	_walk_t += delta
	_idle_breath()

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
		_model.position.y = 0.41 + absf(sin(_walk_t * WALK_BOB_SPEED)) * WALK_BOB_AMP

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
			_model.position.y = 0.41 + absf(sin(_walk_t * WALK_BOB_SPEED * 0.6)) * WALK_BOB_AMP * 0.6
	move_and_slide()

func _turn_to(dir: Vector3, delta: float) -> void:
	var yaw := atan2(dir.x, dir.z)
	rotation.y = lerp_angle(rotation.y, yaw, 8.0 * delta)

func _idle_breath() -> void:
	if _moving or _model == null:
		return
	_model.position.y = 0.41 + sin(_walk_t * 2.2) * 0.02

func _respawn() -> void:
	_hp = max_hp
	_dead = false
	_dead_t = 0.0
	_moving = false
	collision_layer = 2
	velocity = Vector3.ZERO
	global_position = Vector3(randf_range(-11.0, 11.0), 0, randf_range(-11.0, 11.0))
	if _model:
		_model.rotation.x = 0.0
		_model.position.y = 0.41
	_update_label()

func _update_label(text := "") -> void:
	if _hp_label == null:
		return
	_hp_label.text = text if text != "" else "黑狼 HP: %d/%d" % [_hp, max_hp]
