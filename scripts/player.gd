extends CharacterBody3D
## 第一人称控制器：WASD 移动 + 鼠标视角 + 空格跳 + Shift 疾跑 + Esc 释放鼠标
## 持有 BuffSystem（旧版 damageable-entity 状态系统）：受击修正 / DoT / HoT / 移速倍率

signal damaged(hp: int)
signal died
signal healed(hp: int)

const BuffSystemScript := preload("res://scripts/buff_system.gd")

@export var walk_speed := 4.5
@export var sprint_speed := 7.0
@export var jump_velocity := 6.5
@export var crouch_speed := 2.5
@export var ads_speed := 3.0
@export var crouch_ads_speed := 2.2
@export var ground_acceleration := 6.5
@export var air_acceleration := 0.5
@export var move_friction := 6.0
@export var stop_friction := 12.0
@export var slide_min_speed := 6.0
@export var slide_speed_multiplier := 2.0
@export var slide_friction := 1.5
@export var slide_max_time := 2.0
@export var stand_height := 2.0
@export var crouch_height := 1.55
@export var stance_change_speed := 4.0
@export var mouse_sensitivity := 0.0022
@export var max_hp := 100

const GRAVITY := 20.0
const STEP_HEIGHT := 0.5
const STEP_MARGIN := 0.015

var hp := 100
var is_dead := false
var _buffs: BuffSystem = BuffSystem.new()
var is_sprinting := false
var is_sliding := false
var is_crouching := false
var camera_stance_offset := 0.0
var stair_visual_displacement := Vector3.ZERO
var _wants_crouch := false
var _slide_time := 0.0
var _crouch_down := false
var _jump_down := false
var _sprint_was_down := false
var _slide_boost_left := 0.0
var _slide_age := 0.0
var _jump_buffer := 0.0
var _collision: CollisionShape3D
var _capsule: CapsuleShape3D
var _stand_probe: CapsuleShape3D
var _gun: Node

func _ready() -> void:
	_disable_player_shadows(self)
	get_tree().node_added.connect(_on_player_visual_added)
	hp = max_hp
	_buffs = BuffSystem.new()
	collision_layer = 4
	collision_mask = 5  # 1 墙体 + 2 敌人
	_gun = get_node_or_null("Camera3D/Gun")
	for child in get_children():
		if child is CollisionShape3D and child.shape is CapsuleShape3D:
			_collision = child
			_capsule = child.shape.duplicate()
			_collision.shape = _capsule
			_capsule.height = stand_height
			_collision.position.y = stand_height * 0.5
			_stand_probe = _capsule.duplicate()
			_stand_probe.height = stand_height - 0.02
			break
	floor_snap_length = 0.25
	# Keep authored movement speed on uneven wilderness slopes. Without this,
	# CharacterBody3D shortens tangential motion uphill and feels map-dependent.
	floor_constant_speed = true
	Input.mouse_mode = Input.MOUSE_MODE_CAPTURED

func _disable_player_shadows(node: Node) -> void:
	if node is GeometryInstance3D:
		node.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	for child in node.get_children():
		_disable_player_shadows(child)

func _on_player_visual_added(node: Node) -> void:
	# Also cover weapons and attachments installed after the player is ready.
	if node is GeometryInstance3D and is_ancestor_of(node):
		node.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF

func take_damage(d: int, damage_type := "physical", _src: Node3D = null) -> void:
	if is_dead:
		return
	var final_d := maxi(1, floori(d * _buffs.incoming_damage_mul(damage_type)))
	hp = maxi(0, hp - final_d)
	damaged.emit(hp)
	if hp <= 0:
		is_dead = true
		Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
		died.emit()

## 恢复生命（背包药水使用；加法式接口，不改动既有契约）
func heal(amount: int) -> void:
	if is_dead or amount <= 0:
		return
	var before := hp
	hp = mini(max_hp, hp + amount)
	if hp != before:
		healed.emit(hp)

## 通用状态入口（技能/物品给玩家挂 buff 用，如灼锋焰甲）
func apply_buff(type: String, duration_ms: int, opts := {}) -> void:
	if is_dead:
		return
	_buffs.add(type, duration_ms, opts)

func has_buff(type: String) -> bool:
	return _buffs.has(type)

func buff_snapshot() -> Array[Dictionary]:
	return _buffs.effect_snapshot()

func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseMotion and Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
		rotate_y(-event.relative.x * mouse_sensitivity)
		var cam := get_node_or_null("Camera3D") as Camera3D
		if cam:
			cam.rotate_x(-event.relative.y * mouse_sensitivity)
			cam.rotation.x = clampf(cam.rotation.x, -1.45, 1.45)
	elif event is InputEventKey and event.pressed and event.keycode == KEY_ESCAPE:
		Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	elif event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_LEFT:
		if Input.mouse_mode != Input.MOUSE_MODE_CAPTURED:
			Input.mouse_mode = Input.MOUSE_MODE_CAPTURED

func _physics_process(delta: float) -> void:
	_buffs.tick(delta, self)
	var active := not is_dead and Input.mouse_mode == Input.MOUSE_MODE_CAPTURED
	var crouch_down := active and (Input.is_physical_key_pressed(KEY_CTRL) or Input.is_physical_key_pressed(KEY_C))
	var jump_down := active and Input.is_physical_key_pressed(KEY_SPACE)
	var move_input := Vector2.ZERO
	if active:
		move_input = Vector2(
			float(Input.is_physical_key_pressed(KEY_D)) - float(Input.is_physical_key_pressed(KEY_A)),
			float(Input.is_physical_key_pressed(KEY_S)) - float(Input.is_physical_key_pressed(KEY_W))
		).limit_length()
	step_movement(delta, move_input,
		active and Input.is_physical_key_pressed(KEY_SHIFT),
		crouch_down and not _crouch_down, jump_down and not _jump_down,
		active and not get_meta("terrain_editing",false) and Input.is_mouse_button_pressed(MOUSE_BUTTON_RIGHT),
		active and not get_meta("terrain_editing",false) and Input.is_mouse_button_pressed(MOUSE_BUTTON_LEFT),
		_gun != null and _gun.get("_reload_t") > 0.0)
	_crouch_down = crouch_down
	_jump_down = jump_down

func step_movement(delta: float, move_input: Vector2, sprint: bool, crouch_pressed: bool,
		jump_pressed: bool, aiming: bool, firing: bool, reloading_now: bool) -> void:
	# Reload owns the hands, not locomotion; held mouse buttons cannot aim/fire yet.
	aiming = aiming and not reloading_now
	firing = firing and not reloading_now
	var grounded := is_on_floor()
	var horizontal := Vector3(velocity.x, 0, velocity.z)
	var can_stand := can_stand_up()
	var sprint_pressed := sprint and not _sprint_was_down
	_sprint_was_down = sprint
	_slide_boost_left = maxf(0.0, _slide_boost_left - delta)
	_jump_buffer = 0.16 if jump_pressed else maxf(0.0, _jump_buffer - delta)
	if is_sliding:
		_slide_age += delta
	# Holding Shift through slide entry must not immediately cancel crouching.
	if sprint_pressed and not crouch_pressed and can_stand:
		_wants_crouch = false
		is_sliding = false
	if crouch_pressed:
		if is_sliding:
			is_sliding = false
			_wants_crouch = true
		elif not _wants_crouch:
			_wants_crouch = true
			if grounded and horizontal.length() >= slide_min_speed:
				is_sliding = true
				_slide_time = slide_max_time
				_slide_age = 0.0
				if _slide_boost_left <= 0.0:
					horizontal = (horizontal * slide_speed_multiplier).limit_length(sprint_speed * slide_speed_multiplier * _buffs.speed_mul())
					_slide_boost_left = 2.0
		elif can_stand:
			_wants_crouch = false
	if not can_stand:
		_wants_crouch = true
	is_crouching = (_wants_crouch and grounded) or not can_stand
	var slide_jump_ready := not is_sliding or _slide_age >= 0.24 or horizontal.length() <= sprint_speed * 1.75
	if _jump_buffer > 0.0 and grounded and can_stand and slide_jump_ready:
		_wants_crouch = false
		is_crouching = false
		is_sliding = false
		_jump_buffer = 0.0
		velocity.y = jump_velocity
		grounded = false # Preserve horizontal momentum: no ground friction or speed cap on takeoff.
	if is_sliding:
		_slide_time -= delta
		if _slide_time <= 0.0 or horizontal.length() <= crouch_speed or not grounded:
			is_sliding = false
	var direction := global_basis * Vector3(move_input.x, 0, move_input.y)
	is_sprinting = sprint and grounded and not is_crouching and not is_sliding \
		and not aiming and not firing \
		and move_input.length() > 0.7 and direction.normalized().dot(-global_basis.z) > 0.5
	var speed := walk_speed
	if is_sprinting:
		speed = sprint_speed
	elif aiming:
		speed = crouch_ads_speed if is_crouching else ads_speed
	elif is_crouching:
		speed = crouch_speed
	speed *= _buffs.speed_mul()
	if grounded:
		if is_sliding:
			var slope_acceleration := (Vector3.DOWN * GRAVITY).slide(get_floor_normal())
			horizontal += Vector3(slope_acceleration.x, 0, slope_acceleration.z) * delta
		var friction := slide_friction if is_sliding else move_friction if move_input.length_squared() > 0.01 else stop_friction
		horizontal *= exp(-friction * delta)
	if not is_sliding and not direction.is_zero_approx():
		var wish := direction.normalized()
		var wish_speed := speed * move_input.length()
		var remaining := maxf(0.0, wish_speed - horizontal.dot(wish))
		var acceleration := ground_acceleration if grounded else air_acceleration
		horizontal += wish * minf(remaining, acceleration * delta * wish_speed)
		if grounded:
			horizontal = horizontal.limit_length(speed)
	velocity.x = horizontal.x
	velocity.z = horizontal.z
	if not grounded:
		velocity.y -= GRAVITY * delta
	elif velocity.y < 0.0:
		velocity.y = -2.0
	_update_stance(delta)
	var stepped := grounded and velocity.y <= 0.0 and _try_step_up(Vector3(velocity.x, 0, velocity.z) * delta)
	if stepped:
		var step_velocity := velocity
		velocity = Vector3.DOWN * 2.0
		move_and_slide()
		velocity.x = step_velocity.x
		velocity.z = step_velocity.z
	else:
		var before_slide := global_position
		move_and_slide()
		if grounded and velocity.y <= 0.0:
			_try_step_down()
			var descent := global_position.y-before_slide.y
			if is_on_floor() and descent < -0.02:
				stair_visual_displacement.y += descent
	if is_sliding and (not is_on_floor() or Vector2(velocity.x, velocity.z).length() < crouch_speed):
		is_sliding = false

func _try_step_up(motion: Vector3) -> bool:
	if _capsule == null or motion.length_squared() < 0.000001:
		return false
	var obstruction := KinematicCollision3D.new()
	if not test_move(global_transform, motion, obstruction):
		return false
	# Probe the complete capsule along an up / forward / down path.
	# Looking slightly ahead lets the rounded foot clear the voxel's sharp edge.
	var lift := Vector3.UP * (STEP_HEIGHT + STEP_MARGIN)
	if test_move(global_transform, lift):
		return false
	var raised := global_transform
	raised.origin += lift
	var forward := motion.normalized() * (motion.length() + _capsule.radius)
	var front := KinematicCollision3D.new()
	if test_move(raised, forward, front):
		forward = front.get_travel()
	if forward.length() < motion.length() * 0.5:
		return false
	raised.origin += forward
	var landing := KinematicCollision3D.new()
	if not test_move(raised, -lift, landing):
		return false
	if landing.get_normal().dot(Vector3.UP) < cos(floor_max_angle):
		return false
	var rise := lift.y + landing.get_travel().y
	if rise <= STEP_MARGIN or rise > STEP_HEIGHT + STEP_MARGIN:
		return false
	# Move through the swept clear route and settle on the tested support.
	global_position += forward + Vector3.UP * rise
	stair_visual_displacement += forward-motion+Vector3.UP*rise
	velocity.y = 0.0
	return true

func _try_step_down() -> void:
	if is_on_floor(): return
	var landing := KinematicCollision3D.new()
	if not test_move(global_transform, Vector3.DOWN*(STEP_HEIGHT+STEP_MARGIN), landing): return
	if landing.get_normal().dot(Vector3.UP) < cos(floor_max_angle): return
	global_position += landing.get_travel()
	apply_floor_snap()

func _update_stance(delta: float) -> void:
	var height := crouch_height if is_crouching else stand_height
	if _capsule:
		_capsule.height = move_toward(_capsule.height, height, stance_change_speed * delta)
		_collision.position.y = _capsule.height * 0.5
	camera_stance_offset = move_toward(camera_stance_offset, -0.8 if is_crouching else 0.0, stance_change_speed * delta)

func can_stand_up() -> bool:
	if _stand_probe == null:
		return true
	var query := PhysicsShapeQueryParameters3D.new()
	query.shape = _stand_probe
	query.transform = global_transform
	query.transform.origin += Vector3.UP * (stand_height * 0.5 + 0.015)
	query.collision_mask = collision_mask
	query.exclude = [get_rid()]
	return get_world_3d().direct_space_state.intersect_shape(query, 1).is_empty()

func movement_camera_state() -> Dictionary:
	return {"speed": Vector2(velocity.x, velocity.z).length(), "grounded": is_on_floor(),
		"sprinting": is_sprinting, "sliding": is_sliding, "stance": camera_stance_offset,
		"stairs": stair_visual_displacement}
