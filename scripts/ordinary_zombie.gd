extends "res://scripts/enemy.gd"
## game-dev 普通僵尸：单业务时钟驱动四动作；不使用父类接近立即扣血。
enum State { IDLE, CHASE, WINDUP, STRIKE, RECOVER, STUNNED, DYING, CORPSE }

const ACTIVE_START := 8.0 / 24.0
const CONTACT_TIME := 9.0 / 24.0
const ACTIVE_END := 11.0 / 24.0
const ATTACK_DURATION := 1.0
const DEATH_DURATION := 2.0
const WALK_REFERENCE_SPEED := 0.305

@export var level := 3
@export var physical_defense := 25.0
@export var aggro_range := 14.0
@export var attack_start_range := 1.25
@export var impact_range := 1.4
@export var impact_half_width := 0.48
@export var corpse_hold := 1.0
@export var walk_reference_speed := WALK_REFERENCE_SPEED
@export var attack_active_start := ACTIVE_START
@export var attack_active_end := ACTIVE_END
@export var attack_duration := ATTACK_DURATION
@export var death_duration := DEATH_DURATION
@export var attack_clip_choices: Array[String] = ["Attack"]
var _attack_clip := "Attack"
var _next_attack_clip := 0
var state: State = State.IDLE
var attack_elapsed := -1.0
var cooldown_remaining := 0.0
var _clip_time := 0.0
var _clip := ""
var _hit_this_attack := false
var _locked_target: Node3D
var _locked_direction := Vector3.FORWARD
var _ap: AnimationPlayer
var _skeleton: Skeleton3D
var _transition_from: Array[Transform3D] = []
var _transition_elapsed := 0.0
const POSE_BLEND_SECONDS := 0.10
const DEATH_BLEND_SECONDS := 0.32

func _ready() -> void:
	super._ready()
	_hp = max_hp
	_ap = _model.find_child("AnimationPlayer", true, false) as AnimationPlayer
	_skeleton = _find_skeleton(_model)
	if _ap:
		_ap.callback_mode_process = AnimationMixer.ANIMATION_CALLBACK_MODE_PROCESS_MANUAL
		for clip in ["Idle", "Walk", "Attack", "Death"] + attack_clip_choices:
			if not _ap.has_animation(clip):
				push_error("OrdinaryZombie missing animation: " + clip)
				continue
			_ap.get_animation(clip).loop_mode = Animation.LOOP_NONE
	_sync_pose("Idle", 0.0)

func take_damage(d: int, damage_type := "physical", source: Node3D = null) -> bool:
	var amount := d
	if damage_type == "physical":
		amount = maxi(1, floori(d * 60.0 / (60.0 + physical_defense)))
	return super.take_damage(amount, damage_type, source)

func _target_alive(target: Node3D) -> bool:
	return is_instance_valid(target) and target.is_inside_tree() and target.has_method("take_damage") and target.get("is_dead") != true

func _physics_process(delta: float) -> void:
	_flash_t = maxf(0.0, _flash_t - delta)
	if _mat:
		_mat.emission_enabled = _flash_t > 0
		_mat.emission = Color(1.0, 0.25, 0.2) if _flash_t > 0 else Color.BLACK
	if _dead:
		_dead_t += delta
		state = State.DYING if _dead_t < death_duration else State.CORPSE
		_sync_pose("Death", minf(_dead_t, death_duration), delta)
		if _dead_t >= death_duration + corpse_hold:
			queue_free()
		return
	_buffs.tick(delta, self)
	if _dead:
		return
	cooldown_remaining = maxf(0.0, cooldown_remaining - delta)
	if _buffs.is_control_locked():
		_cancel_attack()
		state = State.STUNNED
		velocity = Vector3.ZERO
		_sync_pose("Idle", 0.0, delta)
		return
	if _knock_vel.length_squared() > 0.01:
		_cancel_attack()
		state = State.STUNNED
		velocity = _knock_vel
		move_and_slide()
		_knock_vel = _knock_vel.lerp(Vector3.ZERO, minf(1.0, 8.0 * delta))
		_sync_pose("Idle", 0.0, delta)
		return
	if attack_elapsed >= 0.0:
		_tick_attack(delta)
		return
	if not _target_alive(_player):
		_idle(delta)
		return
	var offset := _player.global_position - global_position
	var planar := Vector3(offset.x, 0.0, offset.z)
	var distance := planar.length()
	if distance > aggro_range:
		_idle(delta)
	elif distance <= attack_start_range and absf(offset.y) < 1.4 and not _buffs.has("fear"):
		if cooldown_remaining <= 0.0:
			_start_attack(planar.normalized() if distance > 0.001 else global_basis.z)
		else:
			_idle(delta)
	else:
		state = State.CHASE
		var direction := planar.normalized()
		if _buffs.has("fear"):
			direction = -direction
		_turn_to(direction, delta)
		velocity.x = direction.x * chase_speed * _buffs.speed_mul()
		velocity.z = direction.z * chase_speed * _buffs.speed_mul()
		_move_grounded(delta)
		var actual_speed := Vector2(get_real_velocity().x, get_real_velocity().z).length()
		var duration := _ap.get_animation("Walk").length if _ap and _ap.has_animation("Walk") else 2.25
		_clip_time = fmod(_clip_time + delta * actual_speed / maxf(walk_reference_speed, .01), duration)
		_sync_pose("Walk" if actual_speed > 0.015 else "Idle", _clip_time, delta)

func _move_grounded(delta: float) -> void:
	velocity.y = -0.1 if is_on_floor() else velocity.y - 9.8 * delta
	move_and_slide()

func _idle(delta: float) -> void:
	state = State.IDLE
	velocity.x = 0.0
	velocity.z = 0.0
	_move_grounded(delta)
	var duration := _ap.get_animation("Idle").length if _ap and _ap.has_animation("Idle") else 4.8
	_clip_time = fmod(_clip_time + delta, duration)
	_sync_pose("Idle", _clip_time, delta)

func _start_attack(direction: Vector3) -> void:
	if _buffs.has("fear"):
		return
	_locked_target = _player
	_locked_direction = direction.normalized()
	rotation.y = atan2(_locked_direction.x, _locked_direction.z)
	cooldown_remaining = attack_cd
	attack_elapsed = 0.0
	_hit_this_attack = false
	if not attack_clip_choices.is_empty():
		_attack_clip = attack_clip_choices[_next_attack_clip % attack_clip_choices.size()]
		_next_attack_clip += 1
	state = State.WINDUP
	velocity.x = 0.0
	velocity.z = 0.0
	_sync_pose("Attack", 0.0, 0.0)

func _tick_attack(delta: float) -> void:
	var previous := attack_elapsed
	attack_elapsed += delta
	velocity.x = 0.0
	velocity.z = 0.0
	_move_grounded(delta)
	state = State.WINDUP if attack_elapsed < attack_active_start else (State.STRIKE if attack_elapsed < attack_active_end else State.RECOVER)
	_sync_pose("Attack", minf(attack_elapsed, attack_duration), delta)
	# Interval crossing also works on slow frames, and a target is hit at most once.
	if not _hit_this_attack and previous < attack_active_end and attack_elapsed >= attack_active_start and _can_impact():
		_hit_this_attack = true
		_locked_target.take_damage(contact_damage)
	if attack_elapsed >= attack_duration:
		_cancel_attack()
		state = State.IDLE
		_sync_pose("Idle", 0.0, 0.0)

func _can_impact() -> bool:
	if not _target_alive(_locked_target):
		return false
	var offset := _locked_target.global_position - global_position
	if absf(offset.y) > 1.4:
		return false
	var horizontal := Vector3(offset.x, 0, offset.z)
	var forward := horizontal.dot(_locked_direction)
	var sideways := absf(horizontal.dot(_locked_direction.cross(Vector3.UP)))
	if forward < 0.0 or forward > impact_range or sideways > impact_half_width:
		return false
	var query := PhysicsRayQueryParameters3D.create(global_position + Vector3.UP, _locked_target.global_position + Vector3.UP, 1 | 4, [get_rid()])
	var hit := get_world_3d().direct_space_state.intersect_ray(query)
	return hit.is_empty() or hit.get("collider") == _locked_target

func _cancel_attack() -> void:
	attack_elapsed = -1.0
	_locked_target = null
	_hit_this_attack = false

func apply_stun(duration_ms: int) -> void:
	super.apply_stun(duration_ms)
	_cancel_attack()

func apply_freeze(duration_ms: int) -> void:
	super.apply_freeze(duration_ms)
	_cancel_attack()

func _die() -> void:
	if _dead:
		return
	_cancel_attack()
	velocity = Vector3.ZERO
	state = State.DYING
	super._die()
	collision_mask = 0
	_sync_pose("Death", 0.0, 0.0)

func _sync_pose(clip: String, time: float, delta: float = -1.0) -> void:
	if clip == "Attack":
		clip = _attack_clip
	if _ap == null or not _ap.has_animation(clip):
		return
	if _clip != clip:
		_transition_from.clear()
		_transition_elapsed = 0.0
		if delta >= 0.0 and _skeleton and not _clip.is_empty():
			for i in _skeleton.get_bone_count():
				_transition_from.append(_skeleton.get_bone_pose(i))
		_clip = clip
		_ap.play(clip)
	_ap.seek(time, true)
	# Blend only the displayed pose. Attack/Death clocks and hit windows keep
	# advancing without delay; the blend finishes well before attack contact.
	# Explicit sampling (delta omitted) stays exact for previews and inspection.
	if delta < 0.0:
		_transition_from.clear()
	elif not _transition_from.is_empty() and _skeleton:
		_transition_elapsed += delta
		# Carry the struck pose into the first knee buckle instead of resetting
		# an outstretched attack arm to idle in a tenth of a second.
		var blend_seconds := DEATH_BLEND_SECONDS if clip == "Death" else POSE_BLEND_SECONDS
		var weight := clampf(_transition_elapsed / blend_seconds, 0.0, 1.0)
		weight = weight * weight * (3.0 - 2.0 * weight)
		for i in _skeleton.get_bone_count():
			_skeleton.set_bone_pose(i, _transition_from[i].interpolate_with(_skeleton.get_bone_pose(i), weight))
		if _transition_elapsed >= blend_seconds:
			_transition_from.clear()
	_sync_head_hitbox()
