extends SceneTree
## Real Godot scene/animation + damage, dodge, occlusion, interruption, lifecycle.
var failures := 0
var kills := 0
var zombie: Node3D
var target: CharacterBody3D
var world: Node3D
class Target extends CharacterBody3D:
	var hp := 1000
	var hits := 0
	var is_dead := false
	func take_damage(d: int) -> void:
		hp -= d
		hits += 1

func _initialize() -> void:
	call_deferred("_run")

func check(ok: bool, label: String) -> void:
	print("ZOMBIE_TEST ", label, " ", "PASS" if ok else "FAIL")
	if not ok:
		failures += 1

func _spawn() -> void:
	zombie = load("res://scenes/enemies/ordinary_zombie.tscn").instantiate()
	world.add_child(zombie)
	zombie.setup(target, func(): kills += 1)
	zombie.set_physics_process(false)
	zombie.position = Vector3.ZERO
	target.position = Vector3(0, 0, 1)

func _advance(seconds: float) -> void:
	for i in int(round(seconds * 120)):
		zombie._physics_process(1.0 / 120.0)

func _run() -> void:
	world = Node3D.new()
	root.add_child(world)
	current_scene = world
	target = Target.new()
	target.collision_layer = 4
	world.add_child(target)
	var floor_body := StaticBody3D.new()
	var shape := CollisionShape3D.new()
	var box := BoxShape3D.new()
	box.size = Vector3(30, 0.2, 30)
	shape.shape = box
	floor_body.add_child(shape)
	floor_body.position.y = -0.1
	world.add_child(floor_body)
	_spawn()
	await physics_frame
	check(zombie._hp == 120 and zombie.contact_damage == 13 and zombie.attack_cd == 2.0, "configured_stats")
	for name in ["Idle", "Walk", "Attack", "Death"]:
		check(zombie._ap != null and zombie._ap.has_animation(name), "clip_" + name)
	zombie._physics_process(0.01)
	check(zombie.state == zombie.State.WINDUP and target.hits == 0, "windup_no_damage")
	_advance(0.30)
	check(target.hits == 0, "before_active_window_no_damage")
	_advance(0.10)
	check(target.hits == 1 and target.hp == 987, "active_window_one_hit_13")
	_advance(0.70)
	check(target.hits == 1 and zombie.cooldown_remaining > 0, "no_repeated_hit_and_cooldown")
	zombie.cooldown_remaining = 0
	zombie._start_attack(Vector3(0, 0, 1))
	target.position = Vector3(2, 0, 1)
	_advance(0.5)
	check(target.hits == 1, "sidestep_misses_locked_direction")
	zombie._cancel_attack()
	target.position = Vector3(0, 0, -1)
	zombie._start_attack(Vector3(0, 0, 1))
	_advance(0.5)
	check(target.hits == 1, "behind_misses")
	zombie._cancel_attack()
	target.position = Vector3(0, 0, 1)
	zombie._start_attack(Vector3(0, 0, 1))
	zombie.apply_stun(1000)
	_advance(.5)
	check(target.hits == 1 and zombie.state == zombie.State.STUNNED, "stun_cancels_attack")
	zombie._buffs.clear()
	var wall := StaticBody3D.new()
	var wall_shape := CollisionShape3D.new()
	var wall_box := BoxShape3D.new()
	wall_box.size = Vector3(2, 2, .15)
	wall_shape.shape = wall_box
	wall.add_child(wall_shape)
	wall.position = Vector3(0, 1, .5)
	world.add_child(wall)
	await physics_frame
	zombie.position = Vector3.ZERO
	zombie._start_attack(Vector3(0, 0, 1))
	_advance(.5)
	check(target.hits == 1, "wall_blocks_hit")
	wall.queue_free()
	await physics_frame
	zombie._cancel_attack()
	zombie.position = Vector3.ZERO
	zombie._start_attack(Vector3(0, 0, 1))
	zombie._tick_attack(.6)
	check(target.hits == 2, "slow_frame_crosses_active_window")
	zombie._cancel_attack()
	zombie.take_damage(85)
	check(zombie._hp == 60, "physical_armor_25")
	zombie.take_damage(10, "fire")
	check(zombie._hp == 50, "elemental_bypasses_physical_armor")
	zombie.cooldown_remaining = 0
	target.position = Vector3(0, 0, 6)
	await physics_frame
	zombie._physics_process(1.0 / 60)
	check(zombie.state == zombie.State.CHASE, "chase_state")
	target.position = Vector3(0, 0, 30)
	zombie._physics_process(1.0 / 60)
	check(zombie.state == zombie.State.IDLE, "outside_aggro_idle")
	target.position = Vector3(0, 0, 1)
	zombie._start_attack(Vector3(0, 0, 1))
	zombie.take_damage(9999)
	zombie.take_damage(9999)
	var hits_before: int = target.hits
	_advance(2.1)
	check(zombie.state == zombie.State.CORPSE and zombie._clip == "Death", "death_to_corpse")
	check(kills == 1 and target.hits == hits_before and zombie.collision_layer == 0, "death_cancels_damage_one_kill")
	check(not zombie.is_queued_for_deletion(), "corpse_held")
	_advance(1)
	check(zombie.is_queued_for_deletion(), "corpse_removed_after_three_seconds")
	world.queue_free()
	await process_frame
	print("ZOMBIE_TEST failures=", failures)
	quit(0 if failures == 0 else 1)
