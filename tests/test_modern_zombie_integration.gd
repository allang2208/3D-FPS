extends SceneTree
## Real main spawn, inherited dungeon driver, alternating native clips and grounding.
var OUT := ProjectSettings.globalize_path("res://tools/ai-gen/humanoid-detail-v02-20260906/runtime-modern")
var failures := 0
func _initialize() -> void:
	call_deferred("run_checks")
func check(ok: bool, label: String) -> void:
	print("MODERN_ZOMBIE ",label," ","PASS" if ok else "FAIL")
	if not ok:failures+=1
func run_checks() -> void:
	var main=load("res://scenes/main.tscn").instantiate()
	root.add_child(main)
	current_scene=main
	# A --script harness sets current_scene after _ready; rebind the real HUD.
	root.get_node("HUD").ensure_for_current_scene()
	await process_frame
	var zombie: Node3D=main.get_node("OrdinaryZombie")
	for child in main.get_children():
		if child is CharacterBody3D and child!=zombie:child.set_physics_process(false)
	var player: Node3D=main.get_node("Player")
	player.position=Vector3(-3,0,4)
	check(zombie._model.scene_file_path=="res://assets/models/modern_zombie/modern_zombie_v02.glb","actual_main_uses_modern_asset")
	var start: Vector3=zombie.global_position
	for i in 120:await physics_frame
	var distance=Vector2(zombie.global_position.x-start.x,zombie.global_position.z-start.z).length()
	print("MODERN_ZOMBIE chase_distance_m=",distance," floor_y=",zombie.global_position.y)
	check(distance>.9 and distance<1.5 and zombie._clip=="Walk","actual_main_chase_and_limp")
	check(absf(zombie.global_position.y-start.y)<.08 and zombie.is_on_floor(),"actual_ground_contact")
	zombie.set_physics_process(false)
	zombie._start_attack(Vector3.BACK)
	var first: String=zombie._clip
	zombie._cancel_attack()
	zombie._start_attack(Vector3.BACK)
	check(first=="Attack" and zombie._clip=="AttackRight","alternating_authored_attacks")
	check(absf(zombie._ap.get_animation("Attack").length-zombie.attack_duration)<.001,"attack_clip_matches_authoritative_clock")
	check(absf(zombie._ap.get_animation("Death").length-zombie.death_duration)<.001,"death_clock_matches_clip")
	var dungeon=load("res://scenes/enemies/ordinary_zombie.tscn").instantiate()
	dungeon.set_script(load("res://scripts/dungeon_zombie.gd"))
	main.add_child(dungeon)
	dungeon.set_physics_process(false)
	check(dungeon.attack_clip_choices.size()==2 and absf(dungeon.attack_active_start-.60)<.001 and absf(dungeon.death_duration-2.4)<.001,"dungeon_script_keeps_new_motion_contract")
	check(dungeon._head_bone>=0 and dungeon.head_hitbox_offset.distance_to(zombie.head_hitbox_offset)<.001,"dungeon_head_anchor_preserved")
	dungeon.queue_free()
	if DisplayServer.get_name()!="headless":
		DirAccess.make_dir_recursive_absolute(OUT)
		var cam=Camera3D.new()
		main.add_child(cam)
		cam.current=true
		cam.fov=40
		for entry in [["Idle",.5],["Walk",.7],["Attack",.65],["Death",2.4]]:
			var clip: String=entry[0]
			zombie._sync_pose(clip,entry[1])
			cam.global_position=zombie.global_position+Vector3(-2.5,1.7,3.3)
			cam.look_at(zombie.global_position+Vector3(0,.85 if clip!="Death" else .25,0))
			for i in 3:await process_frame
			await RenderingServer.frame_post_draw
			root.get_texture().get_image().save_png(OUT.path_join(clip+"-main.png"))
	# Keep the current scene alive until engine shutdown, as in normal gameplay.
	print("MODERN_ZOMBIE_INTEGRATION failures=",failures)
	quit(1 if failures else 0)
