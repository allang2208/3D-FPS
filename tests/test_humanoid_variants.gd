extends SceneTree
var failures := 0
var kills := 0
class Target extends CharacterBody3D:
	var hp := 1000
	var hits := 0
	var is_dead := false
	func take_damage(d: int) -> void:
		hp -= d
		hits += 1
func _initialize() -> void:
	call_deferred("run_checks")
func check(ok: bool, label: String) -> void:
	print("VARIANT ", label, " ", "PASS" if ok else "FAIL")
	if not ok: failures += 1
func run_checks() -> void:
	var world := Node3D.new()
	root.add_child(world)
	current_scene = world
	var floor_body := StaticBody3D.new()
	var col := CollisionShape3D.new()
	var shape := BoxShape3D.new()
	shape.size = Vector3(40, .2, 40)
	col.shape = shape
	floor_body.add_child(col)
	floor_body.position.y = -.1
	world.add_child(floor_body)
	var target := Target.new()
	target.collision_layer = 4
	world.add_child(target)
	for entry in [["miner_workwear_zombie", .35, 160, 16], ["runner_zombie", 2.8, 90, 11]]:
		var path: String = "res://scenes/enemies/" + entry[0] + ".tscn"
		var zombie = load(path).instantiate()
		world.add_child(zombie)
		zombie.setup(target, func(): kills += 1)
		target.position = Vector3(0, 0, 10)
		await physics_frame
		var start: Vector3 = zombie.global_position
		for i in 60: await physics_frame
		zombie.set_physics_process(false)
		var distance: float = zombie.global_position.distance_to(start)
		check(absf(distance-entry[1]) < .09 and zombie._clip == "Walk", entry[0]+" actual_movement_and_native_locomotion")
		check(zombie.is_on_floor() and absf(zombie.position.y) < .04, entry[0]+" ground_contact")
		check(zombie._hp == entry[2] and zombie.contact_damage == entry[3], entry[0]+" stats")
		check(zombie._head_bone >= 0 and zombie._head_hitbox.position.y > 1.0, entry[0]+" animated_head_anchor")
		var sk: Skeleton3D = zombie._skeleton
		zombie._sync_pose("Walk", 0.0)
		var first_pose: Array[Transform3D] = []
		for i in sk.get_bone_count(): first_pose.append(sk.get_bone_pose(i))
		zombie._sync_pose("Walk", zombie._ap.get_animation("Walk").length)
		var error := 0.0
		for i in sk.get_bone_count():
			var pose := sk.get_bone_pose(i)
			error = maxf(error, pose.origin.distance_to(first_pose[i].origin)*.01)
			for axis in 3: error=maxf(error,pose.basis[axis].distance_to(first_pose[i].basis[axis]))
		check(error < .0001, entry[0]+" loop_closes")
		for clip in ["Idle", "Walk", "Attack"]:
			zombie._sync_pose(clip, .65)
			await physics_frame
			await physics_frame
			var head: Vector3 = zombie.get_head_center_global()
			var hit := world.get_world_3d().direct_space_state.intersect_ray(PhysicsRayQueryParameters3D.create(head+Vector3(0,0,2),head,2))
			check(hit.get("collider") == zombie and zombie.get_shape_multiplier(hit.get("shape", -1)) == 2.0, entry[0]+" "+clip+" head_ray_critical")
		var duplicate = load(path).instantiate()
		world.add_child(duplicate)
		duplicate.set_physics_process(false)
		check(duplicate._mat != zombie._mat, entry[0]+" independent_damage_flash")
		duplicate.queue_free()
		zombie.position = Vector3.ZERO
		target.position = Vector3(0,0,1)
		target.hits = 0
		zombie._start_attack(Vector3.BACK)
		zombie._tick_attack(.59)
		check(target.hits == 0, entry[0]+" windup_no_hit")
		zombie._tick_attack(.20)
		zombie._tick_attack(.10)
		check(target.hits == 1, entry[0]+" slow_frame_single_contact")
		zombie._cancel_attack()
		zombie._start_attack(Vector3.BACK)
		check(zombie._clip == "AttackRight", entry[0]+" alternating_right_attack")
		zombie.apply_freeze(1000)
		zombie._physics_process(.8)
		check(target.hits == 1 and zombie.state == zombie.State.STUNNED, entry[0]+" freeze_interrupts")
		zombie._buffs.clear()
		zombie._start_attack(Vector3.BACK)
		target.position.x=2
		zombie._tick_attack(.8)
		check(target.hits == 1, entry[0]+" sidestep_misses")
		var prior_kills := kills
		zombie.take_damage(9999)
		zombie.take_damage(9999)
		zombie._physics_process(2.5)
		check(kills == prior_kills+1 and zombie.state == zombie.State.CORPSE and target.hits == 1, entry[0]+" death_cancels_hit_and_counts_once")
		zombie._physics_process(1.1)
		await process_frame
		check(not is_instance_valid(zombie), entry[0]+" corpse_removed")
	print("HUMANOID_VARIANTS failures=", failures)
	quit(1 if failures else 0)
