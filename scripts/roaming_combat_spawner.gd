extends Node
## Test-only encounter director. All enemies retain their real physics/attacks.
const INNER := 18.0
const OUTER := 32.0
const RETIRE := 85.0
var study: Node3D
var enabled := true
var target_count := 30
var spawned := 0
var retired := 0
var alive := 0
var _clock := 0.0
var _ammo_clock := 0.0
var _rng := RandomNumberGenerator.new()
var _capsule := CapsuleShape3D.new()

func _ready() -> void:
	_rng.randomize()
	_capsule.radius = 0.65
	_capsule.height = 2.2

func _physics_process(delta: float) -> void:
	if not is_instance_valid(study) or not study.prepared or not is_instance_valid(study.player):
		return
	_clock -= delta
	if _clock > 0.0:
		return
	_clock = 0.5
	if enabled and not study.spawning and not study.player.is_dead:
		update_population()
	_ammo_clock -= 0.5
	if _ammo_clock <= 0.0:
		_ammo_clock = 4.0
		study.gun.reserve = maxi(study.gun.reserve, 600)
	study.label.text = "周边刷怪 %s · 存活 %d/%d · 击杀 %d · F11: 10/30/60 · F12: 工头测试\n测试生命值 / 自动补弹 / 正常换弹" % ["开启" if enabled else "暂停", alive, target_count, study.kills]

func update_population() -> void:
	alive = 0
	var farthest: Node3D
	var farthest_distance := 0.0
	for actor in study.actors.get_children():
		if not actor is CharacterBody3D or actor.is_queued_for_deletion():
			continue
		var distance: float = actor.global_position.distance_to(study.player.global_position)
		if distance > RETIRE or actor.position.y < -100:
			actor.queue_free()
			retired += 1
			continue
		if actor.get("_dead") == true:
			continue
		alive += 1
		if distance > farthest_distance:
			farthest = actor
			farthest_distance = distance
	if alive > target_count and is_instance_valid(farthest):
		farthest.queue_free()
		retired += 1
		alive -= 1
		return
	if alive >= target_count:
		return
	var point = choose_point()
	if point == null:
		return
	var kind: String = study.TYPES[spawned % study.TYPES.size()]
	var actor = study.packs[kind].instantiate()
	actor.position = point
	actor.set_meta("study_kind", kind)
	actor.set_meta("roaming_spawn", true)
	# Encounter-only awareness: don't leave actors idling beyond their authored 14 m range.
	actor.aggro_range = 48.0
	actor.setup(study.player, func(): study.kills += 1)
	study.actors.add_child(actor)
	spawned += 1
	alive += 1

func choose_point() -> Variant:
	var origin: Vector3 = study.player.global_position
	var space = study.world.get_world_3d().direct_space_state
	var camera: Camera3D = study.player.get_node("Camera3D")
	for attempt in 8:
		var angle := _rng.randf_range(-PI, PI)
		var radius := _rng.randf_range(INNER, OUTER)
		var point := origin + Vector3(sin(angle), 0, cos(angle)) * radius
		var ground: float = study.world.terrain.data.get_height(point)
		if not is_finite(ground) or absf(ground - origin.y) > 7.0:
			continue
		point.y = ground
		if camera.is_position_in_frustum(point + Vector3.UP):
			continue
		# Match the actual authored river footprint, not a global water-height guess.
		if absf(point.z - study.world._river_center_z(point.x)) < study.world.stream_half_width(point.x) + 1.2:
			continue
		var hit: Dictionary = space.intersect_ray(PhysicsRayQueryParameters3D.create(point + Vector3.UP * 2.5, point - Vector3.UP * 2, 1))
		if hit.is_empty() or hit.normal.y < 0.80 or absf(hit.position.y - ground) > 0.45:
			continue
		point = hit.position + Vector3.UP * 0.06
		var query := PhysicsShapeQueryParameters3D.new()
		query.shape = _capsule
		query.collision_mask = 1 | 2 | 4
		query.transform = Transform3D(Basis.IDENTITY, point + Vector3.UP * 1.15)
		if not space.intersect_shape(query, 1).is_empty():
			continue
		return point
	return null
