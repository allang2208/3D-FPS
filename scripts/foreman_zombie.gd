extends "res://scripts/ordinary_zombie.gd"
## Original foreman: variable-frame whip timing, immediate rally, grounded authored clips.
signal mine_cave_requested(foreman: Node3D)
const CONTACT := .59625
const WHIP_SECONDS := 1.5
const WHIP_REACH_MULTIPLIER := 2.0 # V07: doubled 3.2 m whip, user-approved reach.
var config: Dictionary
var action := ""
var combat_state: StringName = &"idle"
var howl_remaining := 0.0
var _walk_sound := 0.0
var _sound_done := false
var _audio: AudioStreamPlayer3D
var _streams: Dictionary = {}
var _cave_requested := false
var _cave_retry := 0.0

func _ready() -> void:
	config = JSON.parse_string(FileAccess.get_file_as_string("res://assets/models/foreman_zombie/source-config.json"))
	max_hp = int(config.maxHp)
	contact_damage = roundi((float(config.str)+float(config.dex))*.5)
	physical_defense = floorf(float(config.con)*1.5+float(config.str)*.3)
	attack_start_range = float(config.attackSkills.whip.range)*.01*WHIP_REACH_MULTIPLIER
	impact_range = attack_start_range
	impact_half_width = float(config.attackSkills.whip.width)*.005 + .25
	attack_cd = float(config.attackSkills.whip.cooldown)*.001
	walk_reference_speed = .32/(1.5*.65)
	level = int(config.level)
	aggro_range = 25
	set_meta("inspire_attack_consumed",true)
	super._ready()
	_audio = AudioStreamPlayer3D.new()
	_audio.bus = "SFX"
	_audio.max_distance = 22
	_audio.volume_db = -8
	add_child(_audio)
	for id in ["walk","whip","howl","death"]:
		_streams[id] = load("res://assets/models/foreman_zombie/%s.mp3" % id)
	if _ap and _ap.has_animation("Howl"):
		_ap.get_animation("Howl").loop_mode = Animation.LOOP_NONE
	add_to_group("foreman_zombies")

func _physics_process(delta: float) -> void:
	if _dead:
		_dead_t += delta
		state = State.DYING if _dead_t < 1.4 else State.CORPSE
		combat_state = &"dying" if _dead_t < 1.4 else &"corpse"
		_sync_pose("Death",minf(_dead_t,1.4),delta)
		if not _sound_done and _dead_t >= .8:
			_sound_done = true
			_sound("death")
		if _dead_t > 2.4:
			_fade(_model,clampf((_dead_t-2.4)/.3,0,1))
		if _dead_t >= 2.7:
			queue_free()
		return
	_cave_retry=maxf(0,_cave_retry-delta)
	if not _cave_requested and _cave_retry<=0:
		_cave_requested = load("res://scripts/foreman_mine_cave.gd").ensure(self)
		_cave_retry=.5
		if _cave_requested:mine_cave_requested.emit(self)
	_buffs.tick(delta,self)
	if _dead:
		return
	cooldown_remaining = maxf(0,cooldown_remaining-delta)
	howl_remaining = maxf(0,howl_remaining-delta)
	if _buffs.is_control_locked() or _knock_vel.length_squared()>.01 or _buffs.has("fear"):
		_cancel_attack()
		state = State.STUNNED
		combat_state = &"controlled"
		if _knock_vel.length_squared()>.01:
			velocity = _knock_vel
			_knock_vel = _knock_vel.lerp(Vector3.ZERO,minf(1,delta*8))
		elif _buffs.has("fear") and _target_alive(_player):
			velocity = (global_position-_player.global_position).normalized()*chase_speed*_buffs.speed_mul()
		else:
			velocity = Vector3.ZERO
		_move_grounded(delta)
		_sync_pose("Idle",0,delta)
		return
	if not _target_alive(_player):
		_cancel_attack()
		_idle(delta)
		return
	if not action.is_empty():
		_tick_attack(delta)
		return
	var direction := _player.global_position-global_position
	direction.y = 0
	if direction.length()>aggro_range:
		_idle(delta)
	elif howl_remaining<=0:
		_start_howl()
	elif direction.length()<=attack_start_range and cooldown_remaining<=0:
		_start_attack(direction.normalized())
	elif direction.length()>attack_start_range*.85:
		state = State.CHASE
		combat_state = &"chase"
		_turn_to(direction.normalized(),delta)
		velocity = direction.normalized()*chase_speed*_buffs.speed_mul()
		_move_grounded(delta)
		_clip_time = fmod(_clip_time+delta*Vector2(get_real_velocity().x,get_real_velocity().z).length()/walk_reference_speed,1.5)
		_sync_pose("Walk",_clip_time,delta)
		_walk_sound -= delta
		if _walk_sound<=0:
			_walk_sound=.7
			_sound("walk")
	else:
		_idle(delta)

func _start_attack(direction: Vector3) -> void:
	super._start_attack(direction)
	action = "whip"
	combat_state = &"windup"
	_sound_done = false

func _start_howl() -> void:
	action = "howl"
	combat_state = &"howl"
	state = State.RECOVER
	attack_elapsed = 0
	howl_remaining = float(config.attackSkills.howl.cooldown)*.001
	velocity = Vector3.ZERO
	_sound("howl")
	for enemy in get_tree().current_scene.find_children("*", "CharacterBody3D", true, false):
		if enemy.has_method("apply_inspire") and enemy.get("_dead") != true and (enemy.collision_layer & 2) != 0 and enemy.get_meta("faction", "enemy") == "enemy":
			if enemy._buffs.has("statusImmune"):
				continue
			enemy.apply_inspire(int(config.attackSkills.howl.buffDuration),float(config.attackSkills.howl.speedMul),float(config.attackSkills.howl.atkMul))
			if enemy.get_meta("inspire_attack_consumed",false) != true:
				var adapter = enemy.get_node_or_null("ForemanInspiration")
				if adapter == null:
					adapter = load("res://scripts/foreman_inspiration.gd").new()
					adapter.name = "ForemanInspiration"
					enemy.add_child(adapter)
				adapter.refresh(float(config.attackSkills.howl.atkMul))
	_sync_pose("Howl",0,0)

func _tick_attack(delta: float) -> void:
	attack_elapsed += delta
	velocity.x=0
	velocity.z=0
	_move_grounded(delta)
	var duration := 3.0 if action=="howl" else WHIP_SECONDS
	_sync_pose("Howl" if action=="howl" else "Attack",minf(attack_elapsed,duration),delta)
	if action=="whip":
		state = State.WINDUP if attack_elapsed < CONTACT else (State.STRIKE if attack_elapsed < CONTACT+.06 else State.RECOVER)
		combat_state = &"windup" if state == State.WINDUP else (&"strike" if state == State.STRIKE else &"recover")
		if not _sound_done and attack_elapsed>=.45:
			_sound_done=true
			_sound("whip")
		if not _hit_this_attack and attack_elapsed>=CONTACT:
			_hit_this_attack=true
			if _can_impact():
				_locked_target.take_damage(roundi(contact_damage*float(config.attackSkills.whip.damageMul)*_buffs.atk_mul()),"physical",self)
				if _target_alive(_locked_target) and _locked_target.has_method("apply_buff"):
					_locked_target.apply_buff("bleed",10000,{"source":self,"bleed_stacks":[{"remaining_s":10.0}]})
	if attack_elapsed>=duration:
		_cancel_attack()

func _cancel_attack() -> void:
	action=""
	super._cancel_attack()

func _die() -> void:
	if _dead:
		return
	super._die()
	_sound_done=false
	if not get_tree().get_nodes_in_group("foreman_zombies").any(func(other):return other!=self and not other._dead):
		for cave in get_tree().get_nodes_in_group("foreman_mine_caves"):
			cave.queue_free()

func _sound(id: String) -> void:
	if _audio and _streams.has(id):
		_audio.stream = _streams[id]
		_audio.play()

func _fade(node: Node, amount: float) -> void:
	if node is GeometryInstance3D:
		node.transparency=amount
	for child in node.get_children():
		_fade(child,amount)

func _idle(delta: float) -> void:
	combat_state = &"idle"
	super._idle(delta)
