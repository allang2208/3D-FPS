extends "res://scripts/dungeon_source_enemy.gd"
## Original lantern miner sheets, reused only as the foreman's cave summon.
var _fire_cd := 0.0
var _burns: Array[Dictionary] = []
func _physics_process(delta: float) -> void:
	_tick_burns(delta)
	_fire_cd=maxf(0,_fire_cd-delta)
	if not _dead and _action.is_empty() and is_instance_valid(_player) and not _player.is_dead and not _buffs.is_control_locked() and _knock_vel.length_squared()<.01:
		if _player.global_position.distance_to(global_position)<=6 and _fire_cd<=0:
			_action="lantern"
			_elapsed=0
			_impacted=false
			_fire_cd=8
	if not _dead and _action=="lantern":
		_buffs.tick(delta,self)
		if _buffs.is_control_locked() or _dead or _knock_vel.length_squared()>.01:
			_action=""
			return
		_elapsed+=delta
		_pose("attack2",_elapsed)
		if _elapsed>=.75 and not _impacted:
			_impacted=true
			_launch_lantern()
		if _elapsed>=1.5:
			_action=""
		_tick_projectiles(delta)
		return
	super._physics_process(delta)

func _miner_hit() -> void:
	var original := contact_damage
	contact_damage=roundi(original*1.5)
	super._miner_hit()
	contact_damage=original

func _launch_lantern() -> void:
	var sprite := Sprite3D.new()
	sprite.texture=load("res://assets/models/foreman_zombie/summons/projective.png")
	sprite.billboard=BaseMaterial3D.BILLBOARD_ENABLED
	sprite.pixel_size=.48/sprite.texture.get_width()
	get_parent().add_child(sprite)
	sprite.global_position=global_position+Vector3.UP
	_projectiles.append({"node":sprite,"start":sprite.global_position,"target":_player.global_position,"time":0.0})

func _tick_projectiles(delta: float) -> void:
	for i in range(_projectiles.size()-1,-1,-1):
		var shot: Dictionary=_projectiles[i]
		shot.time+=delta
		var t:=minf(1,shot.time/1.5)
		shot.node.global_position=shot.start.lerp(shot.target,t)+Vector3.UP*sin(t*PI)
		shot.node.rotation.z+=TAU*delta
		if t>=1:
			var patch:=MeshInstance3D.new()
			var disk:=CylinderMesh.new()
			disk.top_radius=2
			disk.bottom_radius=2
			disk.height=.03
			patch.mesh=disk
			var mat:=StandardMaterial3D.new()
			mat.albedo_color=Color(1,.25,.015,.5)
			mat.transparency=BaseMaterial3D.TRANSPARENCY_ALPHA
			mat.emission_enabled=true
			mat.emission=Color(1,.18,.01)
			patch.material_override=mat
			get_parent().add_child(patch)
			patch.global_position=shot.target+Vector3.UP*.025
			_burns.append({"node":patch,"remaining":4.0,"tick":.5})
			shot.node.queue_free()
			_projectiles.remove_at(i)

func _tick_burns(delta: float) -> void:
	for i in range(_burns.size()-1,-1,-1):
		var burn: Dictionary=_burns[i]
		var elapsed:=minf(delta,burn.remaining)
		burn.remaining-=delta
		burn.tick-=elapsed
		while burn.tick<=0:
			burn.tick+=.5
			if is_instance_valid(_player) and not _player.is_dead and _player.global_position.distance_to(burn.node.global_position)<=2:
				_player.take_damage(roundi(floorf((float(config.int)+float(config.wis))*.5)*.75),"magic",self)
		if burn.remaining<=0:
			burn.node.queue_free()
			_burns.remove_at(i)

func _exit_tree() -> void:
	super._exit_tree()
	for burn in _burns:
		if is_instance_valid(burn.node):burn.node.queue_free()
