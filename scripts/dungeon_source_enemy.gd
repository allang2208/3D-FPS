extends "res://scripts/enemy.gd"
## Original miner/ore-spider sheets. One clock drives animation and contact.
const PX := 0.01
var config: Dictionary
var kind := "minerZombie"
var damage_multiplier := 1.0
var _sprite: Sprite3D
var _textures: Dictionary = {}
var _clip := "idle"
var _elapsed := 0.0
var _action := ""
var _cooldowns := {"slam": 0.0, "throw": 0.0}
var _impacted := false
var _aim := Vector3.ZERO
var _death_slam := false
var _defense := 0.0
var _projectiles: Array[Dictionary] = []

func configure(id: String, data: Dictionary) -> void:
	kind = id
	config = data
	max_hp = int(data.maxHp)
	chase_speed = float(data.speed) * PX
	contact_damage = roundi((float(data.str) + float(data.dex)) * 0.5)
	_defense = floorf(float(data.con) * 1.5 + float(data.str) * 0.3)
	var shape := CapsuleShape3D.new()
	shape.radius = float(data.collisionRadius) * PX
	shape.height = maxf(shape.radius * 2, float(data.render.collisionHeight) * PX)
	var collision := CollisionShape3D.new()
	collision.name = "Collision"
	collision.shape = shape
	collision.position.y = shape.height / 2
	add_child(collision)
	_sprite = Sprite3D.new()
	_sprite.name = "Model"
	_sprite.billboard = BaseMaterial3D.BILLBOARD_FIXED_Y
	_sprite.alpha_cut = SpriteBase3D.ALPHA_CUT_DISCARD
	_sprite.alpha_scissor_threshold = 0.1
	_sprite.pixel_size = float(data.render.spriteSize) * PX / 512.0
	for clip in data.clips:
		_textures[clip] = load(data.clips[clip].path)
	var idle_image: Image = _textures.idle.get_image()
	var first := idle_image.get_region(Rect2i(0, 0, 512, 512)).get_used_rect()
	_sprite.position.y = (first.end.y - 256) * _sprite.pixel_size
	add_child(_sprite)
	floor_snap_length = 0.4

func _ready() -> void:
	super._ready()
	_hp = max_hp
	_pose("idle", 0)

func take_damage(d: int, damage_type := "physical", source: Node3D = null) -> bool:
	var amount := roundi(d * damage_multiplier)
	if damage_type == "physical":
		amount = maxi(1, floori(amount * 60.0 / (60.0 + _defense)))
	return super.take_damage(amount, damage_type, source)

func _physics_process(delta: float) -> void:
	_tick_projectiles(delta)
	if _dead:
		_dead_t += delta
		if _death_slam:
			var slam: Dictionary = config.attackSkills.slam
			var duration: float = float(slam.duration) / 1000.0
			var end: float = float(config.death.slamFrames) / float(slam.frames) * duration
			if not _impacted and _dead_t >= float(slam.hitFrame) / float(slam.frames) * duration:
				_impacted = true
				_slam()
			if _dead_t < end:
				_pose("slam", _dead_t)
				return
			_pose("death", _dead_t - end)
			_fade_corpse(_dead_t - end, float(config.death.dyingMs + config.death.holdMs) / 1000.0)
			if _dead_t >= end + float(config.death.dyingMs + config.death.holdMs + config.death.fadeMs) / 1000.0:
				queue_free()
		else:
			_pose("death", _dead_t)
			_fade_corpse(_dead_t, float(config.death.animMs + config.death.holdMs) / 1000.0)
			if _dead_t >= float(config.death.animMs + config.death.holdMs + config.death.fadeMs) / 1000.0:
				queue_free()
		return
	_buffs.tick(delta, self)
	if _dead:
		return
	for key in _cooldowns:
		_cooldowns[key] = maxf(0, _cooldowns[key] - delta)
	if _buffs.is_control_locked():
		_action = ""
		velocity = Vector3.ZERO
		_pose("idle", 0)
		return
	if not is_instance_valid(_player) or _player.is_dead:
		return
	if _knock_vel.length_squared() > .01:
		_action = ""
		velocity = _knock_vel
		move_and_slide()
		_knock_vel = _knock_vel.lerp(Vector3.ZERO, minf(1, delta * 8))
		return
	if not _action.is_empty():
		_elapsed += delta
		var skill: Dictionary = config.attackSkills[_action]
		var duration := float(skill.duration) / 1000.0
		var contact := float(skill.get("hitFrame", skill.get("fireFrame", 0))) / float(skill.frames) * duration
		_pose("attack" if _action == "throw" or kind == "minerZombie" else "slam", _elapsed)
		if not _impacted and _elapsed >= contact:
			_impacted = true
			if _action == "throw":
				_launch_crystal()
			elif kind == "oreSpider":
				_slam()
			else:
				_miner_hit()
		if _elapsed >= duration:
			_action = ""
		return
	var difference := _player.global_position - global_position
	difference.y = 0
	var distance := difference.length()
	var skills: Dictionary = config.attackSkills
	if distance <= float(skills.slam.range) * PX and _cooldowns.slam <= 0:
		_start("slam")
	elif kind == "oreSpider" and distance <= float(skills.throw.range) * PX and _cooldowns.throw <= 0:
		_start("throw")
	else:
		var moving := distance > (float(skills.slam.range) * PX * .9)
		var direction := difference.normalized() if moving else Vector3.ZERO
		if _buffs.has("fear"):
			direction = -difference.normalized()
		velocity.x = direction.x * chase_speed * _buffs.speed_mul()
		velocity.z = direction.z * chase_speed * _buffs.speed_mul()
		velocity.y -= 20 * delta
		move_and_slide()
		_elapsed += delta
		_pose("walk" if moving else "idle", _elapsed)
		var camera := get_viewport().get_camera_3d()
		if camera != null and moving:
			_sprite.flip_h = direction.dot(camera.global_basis.x) < 0
	_sync_head_hitbox()

func _start(action: String) -> void:
	_action = action
	_elapsed = 0
	_impacted = false
	_aim = _player.global_position
	_cooldowns[action] = float(config.attackSkills[action].cooldown) / 1000.0
	velocity = Vector3.ZERO

func _visible_target(point: Vector3) -> bool:
	var query := PhysicsRayQueryParameters3D.create(global_position + Vector3.UP * .7, point + Vector3.UP * .7, 1)
	return get_world_3d().direct_space_state.intersect_ray(query).is_empty()

func _miner_hit() -> void:
	if not is_instance_valid(_player) or _player.is_dead:
		return
	var offset := _player.global_position - global_position
	var locked := (_aim - global_position).normalized()
	if offset.length() <= float(config.attackSkills.slam.range) * PX + .25 and offset.normalized().dot(locked) > .65 and _visible_target(_player.global_position):
		_player.take_damage(contact_damage, "physical", self)
		_player.velocity += locked * float(config.attackSkills.slam.knockback) * PX

func _slam() -> void:
	if not is_instance_valid(_player) or _player.is_dead or absf(_player.global_position.y - global_position.y) > 1:
		return
	var distance := Vector2(_player.global_position.x - global_position.x, _player.global_position.z - global_position.z).length()
	for zone in config.attackSkills.slam.zones:
		if distance <= float(zone.radius) * PX and _visible_target(_player.global_position):
			_player.take_damage(roundi(contact_damage * float(zone.damageMul)), "physical", self)
			_player.apply_buff("stun", int(config.attackSkills.slam.stunMs))
			break

func _launch_crystal() -> void:
	var mesh := Sprite3D.new()
	mesh.texture = load("res://assets/dungeon_source/assets/enemies/ore_spider/projective.png")
	mesh.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	mesh.pixel_size = float(config.attackSkills.throw.projectileSize) * PX / mesh.texture.get_width()
	get_parent().add_child(mesh)
	var target := _player.global_position
	_projectiles.append({"node": mesh, "start": global_position + Vector3.UP, "target": target, "time": 0.0})
	mesh.global_position = global_position + Vector3.UP

func _fade_corpse(seconds: float, start: float) -> void:
	if seconds >= start:
		_sprite.alpha_cut = SpriteBase3D.ALPHA_CUT_DISABLED
		_sprite.modulate.a = clampf(1.0 - (seconds - start) / (float(config.death.fadeMs) / 1000.0), 0, 1)

func _tick_projectiles(delta: float) -> void:
	for i in range(_projectiles.size() - 1, -1, -1):
		var shot: Dictionary = _projectiles[i]
		shot.time += delta
		var duration := float(config.attackSkills.throw.flyDuration) / 1000.0
		var t := minf(1, shot.time / duration)
		shot.node.global_position = shot.start.lerp(shot.target, t) + Vector3.UP * sin(t * PI) * float(config.attackSkills.throw.arcHeight) * PX
		shot.node.rotation.y += TAU * delta
		if t >= 1:
			if is_instance_valid(_player) and _player.global_position.distance_to(shot.target) <= float(config.attackSkills.throw.impactRadius) * PX:
				_player.take_damage(roundi(contact_damage * float(config.attackSkills.throw.damageMul)), "physical", self)
			shot.node.queue_free()
			_projectiles.remove_at(i)

func _pose(clip: String, seconds: float) -> void:
	var layout: Dictionary = config.clips[clip]
	if _clip != clip or _sprite.texture == null:
		_clip = clip
		_sprite.texture = _textures[clip]
		_sprite.hframes = int(layout.columns)
		_sprite.vframes = int(layout.rows)
	var progress := seconds * 1000.0 / float(layout.duration_ms)
	var frame := int(floor(progress * int(layout.count)))
	_sprite.frame = frame % int(layout.count) if layout.loop else mini(frame, int(layout.count) - 1)

func _die() -> void:
	if _dead:
		return
	_action = ""
	_death_slam = kind == "oreSpider" and config.death.slamDamage
	_impacted = false
	super._die()

func _exit_tree() -> void:
	for projectile in _projectiles:
		if is_instance_valid(projectile.node):
			projectile.node.queue_free()
