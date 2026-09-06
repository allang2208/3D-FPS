extends SceneTree
## Pose continuity is independent of authoritative attack and death clocks.
var failures := 0
var rig_unit_scale := 1.0
func _initialize() -> void:
	call_deferred("_run")
func check(ok: bool, label: String) -> void:
	print("ZOMBIE_MOTION ", label, " ", "PASS" if ok else "FAIL")
	if not ok: failures += 1
func _poses(s: Skeleton3D) -> Array[Transform3D]:
	var poses: Array[Transform3D] = []
	for i in s.get_bone_count(): poses.append(s.get_bone_pose(i))
	return poses
func _error(a: Array[Transform3D], b: Array[Transform3D]) -> float:
	var error := 0.0
	for i in a.size():
		error = maxf(error, a[i].origin.distance_to(b[i].origin) * rig_unit_scale)
		for axis in 3: error = maxf(error, a[i].basis[axis].distance_to(b[i].basis[axis]))
	return error
func _run() -> void:
	var z: Node3D = load("res://scenes/enemies/ordinary_zombie.tscn").instantiate()
	root.add_child(z)
	z.set_physics_process(false)
	var s: Skeleton3D = z._skeleton
	rig_unit_scale = s.global_basis.get_scale().abs().x
	z._sync_pose("Walk", 1.5)
	var before := _poses(s)
	z._start_attack(Vector3.BACK)
	check(_error(before, _poses(s)) < 0.0001, "walk_to_attack_starts_at_displayed_pose")
	check(z.attack_elapsed == 0.0, "blend_does_not_delay_attack_clock")
	z._sync_pose("Attack", 0.12, 0.12)
	var blended := _poses(s)
	z._sync_pose("Attack", 0.12)
	check(_error(blended, _poses(s)) < 0.0001, "blend_finishes_before_hit_window")
	z._sync_pose("Attack", 0.375)
	before = _poses(s)
	z._sync_pose("Death", 0.0, 0.0)
	check(_error(before, _poses(s)) < 0.0001, "attack_to_death_does_not_snap")
	z._sync_pose("Death", 0.2, 0.2)
	check(not z._transition_from.is_empty(), "death_carries_struck_pose_into_buckle")
	z._sync_pose("Death", 0.34, 0.14)
	check(z._transition_from.is_empty(), "death_blend_completes")
	z._sync_pose("Death", z.death_duration - 0.1)
	before = _poses(s)
	z._sync_pose("Death", z.death_duration)
	# Export resampling may leave < 0.002 local basis/position error near the hold.
	check(_error(before, _poses(s)) < 0.002, "corpse_settles_without_late_rebound")
	before = _poses(s)
	z._sync_pose("Death", z.death_duration, .5)
	check(_error(before, _poses(s)) < 0.0001, "corpse_hold_keeps_exact_final_pose")
	z._sync_pose("Walk", 0.0)
	before = _poses(s)
	z._sync_pose("Walk", z._ap.get_animation("Walk").length)
	check(_error(before, _poses(s)) < 0.0001, "walk_loop_pose_continuity")
	z.queue_free()
	await process_frame
	print("ZOMBIE_MOTION failures=", failures)
	quit(1 if failures else 0)
