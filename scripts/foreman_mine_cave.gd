extends "res://scripts/enemy.gd"
var miner_remaining := 10.0
var lantern_remaining := 45.0

static func ensure(foreman: Node3D) -> bool:
	for cave in foreman.get_tree().get_nodes_in_group("foreman_mine_caves"):
		if cave.get_parent()==foreman.get_parent():return true
	var space=foreman.get_world_3d().direct_space_state
	for i in range(8):
		var direction:=Vector3(sin(i*PI/4),0,cos(i*PI/4))
		var from:=foreman.global_position+Vector3.UP*.8
		var wall=space.intersect_ray(PhysicsRayQueryParameters3D.create(from,from+direction*14,1))
		var point: Vector3=wall.position+wall.normal*.9 if not wall.is_empty() else foreman.global_position+direction*1.8
		var floor_hit=space.intersect_ray(PhysicsRayQueryParameters3D.create(point+Vector3.UP*2,point-Vector3.UP*3,1))
		if floor_hit.is_empty():continue
		point=floor_hit.position
		var query:=PhysicsShapeQueryParameters3D.new()
		var shape:=SphereShape3D.new()
		shape.radius=.6
		query.shape=shape
		query.collision_mask=1|2|4
		query.transform=Transform3D(Basis.IDENTITY,point+Vector3.UP*.65)
		if not space.intersect_shape(query).is_empty():continue
		var cave=load("res://scripts/foreman_mine_cave.gd").new()
		foreman.get_parent().add_child(cave)
		cave.global_position=point
		cave.setup(foreman._player,foreman._kill_cb)
		return true
	return false

func _ready() -> void:
	max_hp=1500
	var collider:=CollisionShape3D.new()
	collider.name="Collision"
	var shape:=CapsuleShape3D.new()
	shape.radius=.6
	shape.height=1.2
	collider.shape=shape
	collider.position.y=.6
	add_child(collider)
	var sprite:=Sprite3D.new()
	sprite.name="Model"
	sprite.texture=load("res://assets/models/foreman_zombie/summons/mine_cave.png")
	sprite.billboard=BaseMaterial3D.BILLBOARD_FIXED_Y
	sprite.pixel_size=1.6/sprite.texture.get_width()
	sprite.position.y=.65
	add_child(sprite)
	super._ready()
	add_to_group("foreman_mine_caves")

func setup(player: Node3D, kill_cb: Callable) -> void:
	super.setup(player,kill_cb)
	apply_status_immune(2147483647)

func _physics_process(delta: float) -> void:
	if _dead:
		queue_free()
		return
	miner_remaining-=delta
	lantern_remaining-=delta
	if miner_remaining<=0:miner_remaining=10 if _spawn(false) else .5
	if lantern_remaining<=0:lantern_remaining=45 if _spawn(true) else .5

func _spawn(lantern: bool) -> bool:
	var point:=global_position+Vector3(0,0,1.2)
	var query:=PhysicsShapeQueryParameters3D.new()
	var shape:=SphereShape3D.new()
	shape.radius=.4
	query.shape=shape
	query.transform=Transform3D(Basis.IDENTITY,point+Vector3.UP*.7)
	query.collision_mask=1|2|4
	if not get_world_3d().direct_space_state.intersect_shape(query).is_empty():return false
	var enemy
	if lantern:
		enemy=load("res://scripts/foreman_lantern.gd").new()
		var data: Dictionary=JSON.parse_string(FileAccess.get_file_as_string("res://assets/models/foreman_zombie/summons/config.json")).lantern
		data.clips.slam=data.clips.attack
		data.attackSkills.slam.knockback=0
		enemy.configure("lanternMinerZombie",data)
	else:
		enemy=load("res://scripts/dungeon_source_enemy.gd").new()
		var data: Dictionary=JSON.parse_string(FileAccess.get_file_as_string("res://assets/models/foreman_zombie/summons/config.json")).miner
		enemy.configure("minerZombie",data)
	get_parent().add_child(enemy)
	enemy.global_position=point
	enemy.setup(_player,_kill_cb)
	return true

func apply_knockback(_direction: Vector3,_force: float) -> void:
	pass
