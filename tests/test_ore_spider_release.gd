extends SceneTree
var failures := 0
var releases: Array[Node3D] = []
var kills := 0
var slams: Array[bool] = []
func _initialize() -> void: call_deferred("_run")
func check(ok: bool, label: String) -> void:
	print("ORE ", label, " ", "PASS" if ok else "FAIL")
	if not ok: failures += 1
func _run() -> void:
	var world := Node3D.new()
	root.add_child(world)
	current_scene = world
	var target := CharacterBody3D.new()
	target.set_script(load("res://scripts/player.gd"))
	target.max_hp = 2000
	var collision := CollisionShape3D.new()
	collision.shape = CapsuleShape3D.new()
	target.add_child(collision)
	world.add_child(target)
	target.set_physics_process(false)
	target.position = Vector3(0, 0, 7)
	var floor_body := StaticBody3D.new()
	var shape := CollisionShape3D.new()
	var box := BoxShape3D.new()
	box.size = Vector3(50, .2, 50)
	shape.shape = box
	floor_body.add_child(shape)
	floor_body.position.y = -.1
	world.add_child(floor_body)
	var z: Node3D = load("res://scenes/enemies/ore_spider.tscn").instantiate()
	world.add_child(z)
	z.set_physics_process(false)
	z.setup(target, func(): kills += 1)
	z._pose("Throw", .85, -1)
	check(z._held.global_position.distance_to(z._throw_origin(false)) < .0001, "held_crystal_follows_palm")
	z._pose("Throw", z.RELEASE_TIME, -1)
	var release_origin: Vector3 = z._throw_origin(false)
	z._pose("Throw", 1.5, -1)
	check(z._throw_origin(true).distance_to(release_origin) < .0001, "slow_frame_samples_exact_release_pose")
	check(is_equal_approx(z._ap.current_animation_position, 1.5), "release_sample_restores_animation_time")
	z._pose("Idle", 0, -1)
	z.crystal_released.connect(func(p: Node3D): p.set_physics_process(false); releases.append(p))
	z.slam_landed.connect(func(final_slam: bool): slams.append(final_slam))
	await physics_frame
	check(z._hp == 650 and z.contact_damage == 45 and z.physical_defense == 46, "source_stats")
	for clip in [["Idle",3.0],["Walk",1.4],["Throw",1.5],["Slam",2.0],["Death",1.2]]:
		check(z._ap.has_animation(clip[0]) and is_equal_approx(z._ap.get_animation(clip[0]).length,clip[1]), "duration_" + clip[0])
	check(z.get_node_or_null("HitboxHead") == null, "crystal_cap_not_fake_head_critical")
	z._start_attack("Throw")
	z._tick_attack(1.10)
	check(releases.is_empty() and target.hp == 2000, "throw_windup_no_damage")
	z._tick_attack(.7)
	check(releases.size() == 1 and target.hp == 2000, "slow_frame_releases_once")
	var p: Node3D = releases[-1]
	check(p.arc_point(.5).y > p.start.y and p.landing.distance_to(target.position) < .05, "arc_and_ground_prediction")
	p._physics_process(1.1)
	check(target.hp == 1944 and p.spent, "stone_lands_once_physical_56")
	var hp: int = target.hp
	z._start_attack("Throw"); z._tick_attack(1.13)
	p = releases[-1]
	target.position.x = 4
	p._physics_process(1.1)
	check(target.hp == hp, "dodge_fixed_landing")
	target.position = Vector3(0,0,2)
	z._start_attack("Slam"); z._tick_attack(1.10)
	check(target.hp == hp, "slam_windup_no_damage")
	z._tick_attack(.05)
	check(target.hp == hp - 90 and target.has_buff("stun"), "inner_slam_double_and_stun")
	z._tick_attack(1)
	check(target.hp == hp - 90 and slams.size() == 1, "slam_no_zone_stacking_or_repeat")
	target.position = Vector3(0,0,4)
	hp = target.hp
	z._start_attack("Slam"); z._tick_attack(2.1)
	check(target.hp == hp - 45, "outer_slam_single_low_fps")
	target.position = Vector3(0,0,6)
	hp = target.hp
	z._start_attack("Slam"); z._tick_attack(2.1)
	check(target.hp == hp, "outside_slam_dodges")
	var count := releases.size()
	z._start_attack("Throw"); z.apply_stun(1000); z._physics_process(.5)
	check(releases.size() == count and z.state == "Idle", "stun_cancels_unreleased_throw")
	z._buffs.clear()
	z._start_attack("Slam"); z.apply_freeze(1000); z._physics_process(.5)
	check(target.hp == hp and z.state == "Idle", "freeze_cancels_slam")
	z._buffs.clear()
	var wall := StaticBody3D.new()
	var wc := CollisionShape3D.new()
	var wb := BoxShape3D.new()
	wb.size = Vector3(8, 6, .3)
	wc.shape = wb
	wall.add_child(wc)
	wall.position = Vector3(0,3,3)
	world.add_child(wall)
	await physics_frame
	check(not z._line_clear(), "wall_blocks_attack_start")
	z._start_attack("Throw"); z._tick_attack(1.13)
	p = releases[-1]; p._physics_process(2)
	check(target.hp == hp and p.spent, "swept_arc_hits_wall")
	target.position = Vector3(0,0,4)
	z._start_attack("Slam"); z._tick_attack(2.1)
	check(target.hp == hp, "wall_blocks_slam")
	wall.queue_free()
	await physics_frame
	z.throw_cd = 99; z.slam_cd = 99
	target.position = Vector3(0,0,12)
	var before := z.global_position
	for i in 30:
		z._physics_process(1.0/60)
		await physics_frame
	check(z.global_position.distance_to(before) > .4 and z.is_on_floor(), "real_grounded_chase_displacement")
	z.position = Vector3.ZERO
	target.position = Vector3(0,0,2)
	hp = target.hp
	z._start_attack("Throw")
	z.take_damage(10000)
	z.take_damage(10000)
	check(kills == 1 and z.collision_layer == 0 and z.state == "DeathSlam", "one_kill_and_death_stage")
	z._tick_death(1.10)
	check(target.hp == hp, "death_slam_telegraph_no_early_damage")
	z._tick_death(.03)
	check(target.hp == hp - 90 and slams[-1], "intentional_death_slam_at_source_time")
	z._tick_death(1.8)
	check(not z.is_queued_for_deletion() and target.hp == hp - 90 and z.state == "Death", "collapse_and_corpse_hold_no_repeat")
	z._tick_death(2)
	check(z.is_queued_for_deletion(), "fade_cleanup")
	world.queue_free()
	await process_frame
	print("ORE_RESULT failures=", failures)
	quit(1 if failures else 0)
