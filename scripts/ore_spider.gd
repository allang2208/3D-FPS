extends "res://scripts/enemy.gd"
## Original oreSpider: throw, concentric slam, intentional final death slam.
signal crystal_released(projectile: Node3D)
signal slam_landed(is_death_slam: bool)
const Crystal := preload("res://scripts/ore_crystal_projectile.gd")
const THROW_SECONDS := 1.5
const RELEASE_TIME := 21.0 / 28.0 * THROW_SECONDS
const SLAM_SECONDS := 2.0
const SLAM_HIT := 10.0 / 18.0 * SLAM_SECONDS
const DEATH_SLAM_SECONDS := 14.0 / 18.0 * SLAM_SECONDS
const DEATH_SECONDS := 1.2
const HOLD_SECONDS := 1.0
const FADE_SECONDS := .3
@export var physical_defense := 46.0
@export var hand_throw := false
@export var level := 6
@export var rank := "elite"
@export var throw_cooldown := 5.5
@export var slam_cooldown := 8.0
@export var crystal_flight := 1.0
@export var crystal_arc_height := 1.4
@export var crystal_radius := 1.4
@export var crystal_damage_multiplier := 1.25
@export var slam_stun_ms := 2000
@export var inner_damage_multiplier := 2.0
@export var outer_damage_multiplier := 1.0
var damage_multiplier := 1.0 # Existing dungeon blessing increases incoming damage.
var _projectiles: Array[Node3D] = []
var _effects: Array[Node3D] = []
@export var throw_range := 8.4
@export var slam_range := 4.9
@export var inner_radius := 2.8
@export var outer_radius := 4.9
@export var aggro_range := 20.0
var state := "Idle"
var elapsed := 0.0
var throw_cd := 0.0
var slam_cd := 0.0
var fired := false
var take_sound := false
var launch_sound := false
var death_hit := false
var _ap: AnimationPlayer
var _skeleton: Skeleton3D
var _clip := ""
var _blend_from: Array[Transform3D] = []
var _blend_time := 0.0
var _warning: MeshInstance3D
var _sound: AudioStreamPlayer3D
var _walk_sound_t := 0.0
var _held: MeshInstance3D

func configure_source(data: Dictionary) -> void:
	max_hp = int(data.maxHp)
	level = int(data.level)
	rank = str(data.rank)
	contact_damage = roundi((float(data.str) + float(data.dex)) * .5)
	physical_defense = floorf(float(data.con) * 1.5 + float(data.str) * .3)
	chase_speed = float(data.speed) * .014
	var throw_data: Dictionary = data.attackSkills["throw"]
	var slam_data: Dictionary = data.attackSkills.slam
	throw_range = float(throw_data.range) * .014
	slam_range = float(slam_data.range) * .014
	inner_radius = float(slam_data.zones[0].radius) * .014
	outer_radius = float(slam_data.zones[1].radius) * .014
	inner_damage_multiplier = float(slam_data.zones[0].damageMul)
	outer_damage_multiplier = float(slam_data.zones[1].damageMul)
	throw_cooldown = float(throw_data.cooldown) / 1000.0
	slam_cooldown = float(slam_data.cooldown) / 1000.0
	crystal_flight = float(throw_data.flyDuration) / 1000.0
	crystal_arc_height = float(throw_data.arcHeight) * .014
	crystal_radius = float(throw_data.impactRadius) * .014
	crystal_damage_multiplier = float(throw_data.damageMul)
	slam_stun_ms = int(slam_data.stunMs)

func _build_head_hitbox() -> void:
	# The crystal cap is armor; no fabricated capsule-top head critical region.
	# Embedded faces have no source weakpoint contract yet.
	pass

func _ready() -> void:
	super._ready()
	_hp = max_hp
	_ap = _model.find_child("AnimationPlayer", true, false) as AnimationPlayer
	_skeleton = _find_skeleton(_model)
	if _ap: _ap.callback_mode_process = AnimationMixer.ANIMATION_CALLBACK_MODE_PROCESS_MANUAL
	_sound = AudioStreamPlayer3D.new()
	_sound.max_distance = 25.0
	add_child(_sound)
	_held = Crystal.make_crystal()
	_model.add_child(_held)
	_pose("Idle", 0.0)

func take_damage(d: int, damage_type := "physical", source: Node3D = null) -> bool:
	var scaled := roundi(d * damage_multiplier)
	var amount := maxi(1, floori(scaled * 60.0 / (60.0 + physical_defense))) if damage_type == "physical" else scaled
	return super.take_damage(amount, damage_type, source)

func _alive() -> bool:
	return is_instance_valid(_player) and _player.is_inside_tree() and _player.get("is_dead") != true

func _physics_process(delta: float) -> void:
	if _dead:
		_tick_death(delta)
		return
	_buffs.tick(delta, self)
	if _dead: return
	throw_cd = maxf(0.0, throw_cd - delta)
	slam_cd = maxf(0.0, slam_cd - delta)
	if _buffs.is_control_locked() or _buffs.has("fear") or _knock_vel.length_squared() > .01:
		_cancel_attack()
		velocity.x = _knock_vel.x
		velocity.z = _knock_vel.z
		if _buffs.has("fear") and _alive():
			var flee := (global_position - _player.global_position).normalized() * chase_speed
			velocity.x += flee.x
			velocity.z += flee.z
		_ground(delta)
		_knock_vel = _knock_vel.lerp(Vector3.ZERO, minf(1.0, delta * 8))
		_pose("Idle", 0, delta)
		return
	if state == "Throw" or state == "Slam":
		_tick_attack(delta)
		return
	velocity.x = 0
	velocity.z = 0
	if _alive():
		var offset := _player.global_position - global_position
		var flat := Vector3(offset.x, 0, offset.z)
		var distance := flat.length()
		if distance < aggro_range:
			rotation.y = lerp_angle(rotation.y, atan2(flat.x, flat.z), minf(1, delta * 5))
			var visible := _line_clear()
			if visible and absf(offset.y) < 1.2 and distance <= slam_range and slam_cd <= 0:
				_start_attack("Slam")
				return
			if visible and distance <= throw_range and throw_cd <= 0:
				_start_attack("Throw")
				return
			if distance > inner_radius or not visible:
				velocity.x = flat.normalized().x * chase_speed * _buffs.speed_mul()
				velocity.z = flat.normalized().z * chase_speed * _buffs.speed_mul()
	_ground(delta)
	var speed := Vector2(get_real_velocity().x, get_real_velocity().z).length()
	state = "Walk" if speed > .02 else "Idle"
	elapsed = fmod(elapsed + delta * (speed / 1.05 if state == "Walk" else 1), 1.4 if state == "Walk" else 3.0)
	_pose(state, elapsed, delta)
	_walk_sound_t -= delta
	if state == "Walk" and _walk_sound_t <= 0:
		_play_sound("walking")
		_walk_sound_t = .4

func _ground(delta: float) -> void:
	velocity.y = -.1 if is_on_floor() else velocity.y - 9.8 * delta
	move_and_slide()

func _line_clear() -> bool:
	if not _alive(): return false
	var ray := PhysicsRayQueryParameters3D.create(global_position + Vector3.UP, _player.global_position + Vector3.UP, 1)
	return get_world_3d().direct_space_state.intersect_ray(ray).is_empty()

func _start_attack(kind: String) -> void:
	if _dead or _buffs.is_control_locked() or _buffs.has("fear"): return
	state = kind
	elapsed = 0
	fired = false
	take_sound = false
	launch_sound = false
	velocity.x = 0
	velocity.z = 0
	if _alive():
		var offset := _player.global_position - global_position
		rotation.y = atan2(offset.x, offset.z)
	if kind == "Throw": throw_cd = throw_cooldown
	else:
		slam_cd = slam_cooldown
		_clear_warning()
		_warning = Crystal.ring(get_parent(), global_position, outer_radius, Color(.85, .12, .22))
	_pose(kind, 0, 0)

func _tick_attack(delta: float) -> void:
	elapsed += delta
	_ground(delta)
	_pose(state, minf(elapsed, THROW_SECONDS if state == "Throw" else SLAM_SECONDS), delta)
	if state == "Throw":
		if not take_sound and elapsed >= 7.0 / 28 * THROW_SECONDS:
			take_sound = true
			_play_sound("taking")
		if not launch_sound and elapsed >= 18.0 / 28 * THROW_SECONDS:
			launch_sound = true
			_play_sound("throwing")
		if not fired and elapsed >= RELEASE_TIME:
			fired = true
			_release()
		if elapsed >= THROW_SECONDS: _cancel_attack()
	else:
		if not fired and elapsed >= SLAM_HIT:
			fired = true
			_slam(false)
		if elapsed >= SLAM_SECONDS: _cancel_attack()

func _release() -> void:
	if not _alive(): return
	var projectile := Crystal.new()
	projectile.start = _throw_origin(true)
	var target_velocity: Vector3 = _player.velocity if _player is CharacterBody3D else Vector3.ZERO
	var intended := _player.global_position + Vector3(target_velocity.x, 0, target_velocity.z) * crystal_flight
	var ray := PhysicsRayQueryParameters3D.create(intended + Vector3.UP * 2, intended - Vector3.UP * 4, 1)
	var floor_hit := get_world_3d().direct_space_state.intersect_ray(ray)
	projectile.landing = floor_hit.position + Vector3.UP * .02 if not floor_hit.is_empty() else Vector3(intended.x, global_position.y, intended.z)
	projectile.damage = roundi(contact_damage * crystal_damage_multiplier)
	projectile.flight_seconds = crystal_flight
	projectile.arc_height = crystal_arc_height
	projectile.radius = crystal_radius
	projectile.target = weakref(_player)
	projectile.source = weakref(self)
	get_parent().add_child(projectile)
	_projectiles = _projectiles.filter(func(p): return is_instance_valid(p))
	_projectiles.append(projectile)
	crystal_released.emit(projectile)

func _slam(final_slam: bool) -> void:
	_clear_warning()
	_play_sound("attacking")
	if _alive() and Crystal.can_hit(self, global_position, _player, outer_radius):
		var d := Vector2(_player.global_position.x - global_position.x, _player.global_position.z - global_position.z).length()
		_player.take_damage(roundi(contact_damage * (inner_damage_multiplier if d <= inner_radius else outer_damage_multiplier)), "physical", self)
		if _player.has_method("apply_buff"): _player.apply_buff("stun", slam_stun_ms)
	var shock := Crystal.ring(get_parent(), global_position, .3, Color(.78, .57, .94))
	_effects = _effects.filter(func(fx): return is_instance_valid(fx))
	_effects.append(shock)
	var tween := shock.create_tween()
	tween.tween_property(shock, "scale", Vector3(outer_radius / .3, .35, outer_radius / .3), .52)
	tween.tween_callback(shock.queue_free)
	slam_landed.emit(final_slam)

func _cancel_attack() -> void:
	state = "Idle"
	elapsed = 0
	_clear_warning()

func _clear_warning() -> void:
	if is_instance_valid(_warning): _warning.queue_free()
	_warning = null

func apply_stun(duration_ms: int) -> void:
	super.apply_stun(duration_ms)
	if not _dead: _cancel_attack()

func apply_freeze(duration_ms: int) -> void:
	super.apply_freeze(duration_ms)
	if not _dead: _cancel_attack()

func _die() -> void:
	if _dead: return
	_cancel_attack()
	velocity = Vector3.ZERO
	super._die()
	collision_mask = 0
	state = "DeathSlam"
	_warning = Crystal.ring(get_parent(), global_position, outer_radius, Color(1, .18, .16))
	_pose("Slam", 0, 0)

func _tick_death(delta: float) -> void:
	_dead_t += delta
	if not death_hit and _dead_t >= SLAM_HIT:
		death_hit = true
		_slam(true)
	if _dead_t < DEATH_SLAM_SECONDS:
		_pose("Slam", _dead_t, delta)
	else:
		if state == "DeathSlam":
			state = "Death"
			_play_sound("dying")
		_pose("Death", minf(_dead_t - DEATH_SLAM_SECONDS, DEATH_SECONDS), delta)
		var fade := clampf((_dead_t - DEATH_SLAM_SECONDS - DEATH_SECONDS - HOLD_SECONDS) / FADE_SECONDS, 0, 1)
		for node in _model.find_children("*", "GeometryInstance3D", true, false): node.transparency = fade
	if _dead_t >= DEATH_SLAM_SECONDS + DEATH_SECONDS + HOLD_SECONDS + FADE_SECONDS: queue_free()

func _pose(clip: String, time: float, delta: float = -1.0) -> void:
	if _held:
		_held.visible = clip == "Throw" and time >= .375 and time < RELEASE_TIME
		_held.position = Vector3(.6, .8, .5).lerp(Vector3(0, 1.15, .9), smoothstep(.375, RELEASE_TIME, time))
	if not _ap or not _ap.has_animation(clip): return
	if clip != _clip:
		_blend_from.clear()
		_blend_time = 0
		if _skeleton and not _clip.is_empty() and delta >= 0:
			for i in _skeleton.get_bone_count(): _blend_from.append(_skeleton.get_bone_pose(i))
		_clip = clip
		_ap.play(clip)
	_ap.seek(time, true)
	if delta < 0: _blend_from.clear()
	elif not _blend_from.is_empty():
		_blend_time += delta
		var weight := smoothstep(0, .12, _blend_time)
		for i in _skeleton.get_bone_count(): _skeleton.set_bone_pose(i, _blend_from[i].interpolate_with(_skeleton.get_bone_pose(i), weight))
		if weight >= 1: _blend_from.clear()
	# This monster deliberately has no head weakpoint to synchronize.
	if hand_throw and _held:
		_held.global_position = _throw_origin(false)

func _throw_origin(at_release: bool) -> Vector3:
	if not hand_throw or not _skeleton:
		return to_global(Vector3(0, 1.15, .9))
	var bone := _skeleton.find_bone("arm_hand")
	if bone < 0: return to_global(Vector3(0, 1.15, .9))
	var restore_time := _ap.current_animation_position
	if at_release: _ap.seek(RELEASE_TIME, true)
	var point := _skeleton.to_global(_skeleton.get_bone_global_pose(bone) * Vector3(0, .12, 0))
	if at_release: _ap.seek(restore_time, true)
	return point

func _play_sound(name_: String) -> void:
	_sound.stream = load("res://assets/sfx/ore_spider/" + name_ + ".mp3")
	_sound.play()

func _exit_tree() -> void:
	_clear_warning()
	for node in _projectiles + _effects:
		if is_instance_valid(node): node.queue_free()
	if _sound:
		_sound.stop()
		_sound.stream = null
