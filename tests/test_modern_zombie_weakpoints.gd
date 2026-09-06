extends SceneTree
## Real projectile/raycast regression on the modern zombie and baseline wolf.
const ProjectileScript := preload("res://scripts/projectile.gd")
var failures := 0
var world: Node3D
var critical_events := 0
var normal_events := 0
func _initialize() -> void:
	call_deferred("_run")
func check(ok: bool, label: String) -> void:
	print("WEAKPOINT ", label, " ", "PASS" if ok else "FAIL")
	if not ok: failures += 1
func make_wolf() -> Node3D:
	var wolf := CharacterBody3D.new()
	wolf.set_script(load("res://scripts/enemy.gd"))
	wolf.max_hp = 1000
	var body := CollisionShape3D.new()
	body.name = "Collision"
	var capsule := CapsuleShape3D.new()
	capsule.radius = 0.55
	capsule.height = 1.1
	body.shape = capsule
	body.position.y = 0.5
	wolf.add_child(body)
	var model: Node3D = load("res://assets/models/wolf_quaternius.gltf").instantiate()
	model.name = "Model"
	model.scale = Vector3.ONE * 0.3
	model.set_script(load("res://scripts/wolf_anim.gd"))
	wolf.add_child(model)
	return wolf
func settle() -> void:
	await physics_frame
	await physics_frame
func ray(from: Vector3, to: Vector3) -> Dictionary:
	return world.get_world_3d().direct_space_state.intersect_ray(PhysicsRayQueryParameters3D.create(from, to, 2))
func _on_hit(critical: bool) -> void:
	if critical: critical_events += 1
	else: normal_events += 1
func shoot(at: Vector3, from: Vector3) -> void:
	var bullet := ProjectileScript.fire(world, from, (at-from).normalized(), 90.0, 25, 0.0)
	bullet.hit_enemy.connect(_on_hit)
	for i in 12: await physics_frame
func _run() -> void:
	world = Node3D.new()
	root.add_child(world)
	current_scene = world
	for species in ["zombie", "wolf"]:
		var scene_path := "res://scenes/enemies/spitter_zombie.tscn" if species == "spitter" else "res://scenes/enemies/ordinary_zombie.tscn"
		var enemy: Node3D = load(scene_path).instantiate() if species != "wolf" else make_wolf()
		world.add_child(enemy)
		enemy.set_physics_process(false)
		enemy._hp = 1000
		var sk: Skeleton3D = enemy._head_skeleton
		var ap: AnimationPlayer = enemy._model.find_child("AnimationPlayer", true, false)
		ap.callback_mode_process = AnimationMixer.ANIMATION_CALLBACK_MODE_PROCESS_MANUAL
		var previous_head := Vector3.ZERO
		var moved := false
		for clip in (["Idle", "Walk", "Attack"] if species != "wolf" else ["Idle", "Gallop", "Attack"]):
			if species != "wolf": enemy._sync_pose(clip, 0.375)
			else:
				ap.play(clip)
				ap.seek(0.375, true)
			await settle()
			var head: Vector3 = enemy.get_head_center_global()
			var bone_world := sk.to_global(sk.get_bone_global_pose(enemy._head_bone) * enemy.head_hitbox_offset)
			check(head.distance_to(bone_world)<0.002, species+"_"+clip+"_follows_animated_bone")
			if previous_head != Vector3.ZERO and previous_head.distance_to(head)>0.01: moved = true
			previous_head = head
			var hit := ray(head+Vector3(0,0,2), head)
			check(hit.get("collider") == enemy and enemy.get_shape_multiplier(hit.get("shape",-1)) == 2.0, species+"_"+clip+"_head_ray_is_critical")
		check(moved, species+"_head_moves_between_poses")
		# Physics shape IDs must not depend on scene-tree sibling ordering.
		enemy.move_child(enemy._head_hitbox, 0)
		enemy._rebuild_shape_multipliers()
		var ordered_head: Vector3 = enemy.get_head_center_global()
		var reordered_hit := ray(ordered_head+Vector3(0,0,2), ordered_head)
		check(reordered_hit.get("collider") == enemy and enemy.get_shape_multiplier(reordered_hit.get("shape",-1))==2.0, species+"_shape_owner_mapping_survives_reorder")
		# Shoot the displayed Attack head and then the lower torso from behind.
		var head: Vector3 = enemy.get_head_center_global()
		var old_hp: int = enemy._hp
		var old_critical := critical_events
		await shoot(head, head+Vector3(0,0,2))
		check(old_hp-enemy._hp == ({"zombie":35,"spitter":31,"wolf":50}[species]), species+"_head_damage_2x_then_armor")
		check(critical_events == old_critical+1, species+"_one_headshot_feedback")
		old_hp = enemy._hp
		var old_normal := normal_events
		await shoot(Vector3(0,0.5,0), Vector3(0,0.5,-2))
		check(old_hp-enemy._hp == ({"zombie":17,"spitter":15,"wolf":25}[species]), species+"_torso_damage_1x_then_armor")
		check(normal_events == old_normal+1, species+"_torso_is_not_critical")
		enemy._die()
		await settle()
		check(ray(head+Vector3(0,0,2),head).is_empty(),species+"_corpse_has_no_weakpoint_hit")
		enemy.queue_free()
		await process_frame
	world.queue_free()
	await process_frame
	print("WEAKPOINT failures=", failures)
	quit(1 if failures else 0)
