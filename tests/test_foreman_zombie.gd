extends SceneTree
class Target extends CharacterBody3D:
	var hp := 10000
	var max_hp := 10000
	var is_dead := false
	var hits := 0
	var buffs: Array = []
	func take_damage(amount: int,_type := "physical",_source: Node3D = null) -> void:
		hp -= amount
		hits += 1
	func apply_buff(id: String,_ms: int,_options := {}) -> void:
		buffs.append(id)
var checks := 0
var failures := 0
var kills := 0
func check(value: bool,message: String) -> void:
	checks+=1
	if not value:
		failures+=1
		push_error(message)
func _initialize() -> void:
	call_deferred("run_test")
func run_test() -> void:
	var world := Node3D.new()
	root.add_child(world)
	current_scene=world
	var floor_body := StaticBody3D.new()
	var col := CollisionShape3D.new()
	var box := BoxShape3D.new()
	box.size=Vector3(40,.2,40)
	col.shape=box
	col.position.y=-.1
	floor_body.add_child(col)
	world.add_child(floor_body)
	var target := Target.new()
	world.add_child(target)
	target.position=Vector3(0,0,2)
	var enemy = load("res://scenes/enemies/foreman_zombie.tscn").instantiate()
	world.add_child(enemy)
	enemy.setup(target,func():kills+=1)
	enemy.set_physics_process(false)
	await physics_frame
	for pair in [["Idle",1.0],["Walk",1.5],["Attack",1.5],["Howl",3.0],["Death",1.4]]:
		check(enemy._ap.has_animation(pair[0]) and is_equal_approx(enemy._ap.get_animation(pair[0]).length,pair[1]),"exported clip duration "+pair[0])
	enemy._start_attack(Vector3.BACK)
	enemy._physics_process(.58)
	check(target.hits==0,"whip windup does not damage")
	enemy._physics_process(.02)
	check(target.hits==1 and target.hp==9910,"variable frame 21 deals physical x2")
	check(target.buffs.has("bleed"),"whip adds original bleed")
	enemy._physics_process(.8)
	check(target.hits==1,"whip contacts once")
	enemy._start_attack(Vector3.BACK)
	target.position.x=1.5
	enemy._physics_process(.7)
	check(target.hits==1,"sidestep avoids locked whip")
	target.position.x=0
	var wall:=StaticBody3D.new()
	var wall_col:=CollisionShape3D.new()
	var wall_shape:=BoxShape3D.new()
	wall_shape.size=Vector3(4,3,.2)
	wall_col.shape=wall_shape
	wall.add_child(wall_col)
	world.add_child(wall)
	wall.position=Vector3(0,1.5,1)
	await physics_frame
	enemy._start_attack(Vector3.BACK)
	enemy._physics_process(.7)
	check(target.hits==1,"wall blocks whip impact")
	wall.queue_free()
	await physics_frame
	check(is_equal_approx(enemy.attack_start_range,6.4) and is_equal_approx(enemy.impact_range,6.4),"long whip starts and hits at doubled 6.4 m reach")
	var prior_hits: int=target.hits
	target.position=Vector3(0,0,6.3)
	enemy._start_attack(Vector3.BACK)
	enemy._physics_process(.58)
	check(target.hits==prior_hits,"extended-range windup still causes no damage")
	enemy._physics_process(.02)
	check(target.hits==prior_hits+1,"downstroke hits near extended range boundary")
	target.position.z=6.5
	enemy._start_attack(Vector3.BACK)
	enemy._physics_process(.7)
	check(target.hits==prior_hits+1,"target beyond 6.4 m avoids whip")
	target.position=Vector3(1.0,0,6.0)
	enemy._start_attack(Vector3.BACK)
	enemy._physics_process(.7)
	check(target.hits==prior_hits+1,"longer whip does not widen locked strike lane")
	target.position=Vector3(0,0,6.0)
	var far_wall:=StaticBody3D.new()
	var far_col:=CollisionShape3D.new()
	far_col.shape=wall_shape
	far_wall.add_child(far_col)
	world.add_child(far_wall)
	far_wall.position=Vector3(0,1.5,4.0)
	await physics_frame
	enemy._start_attack(Vector3.BACK)
	enemy._physics_process(.7)
	check(target.hits==prior_hits+1,"wall in newly extended reach blocks whip")
	far_wall.queue_free()
	await physics_frame
	enemy._cancel_attack()
	enemy.howl_remaining=30
	enemy.cooldown_remaining=0
	enemy._physics_process(.01)
	check(enemy.action=="whip","AI starts downstroke in newly extended range")
	target.position=Vector3(0,0,2)
	var hits_before_stun: int=target.hits
	enemy._start_attack(Vector3.BACK)
	enemy.apply_stun(1000)
	enemy._physics_process(.7)
	check(target.hits==hits_before_stun and enemy.action.is_empty(),"stun cancels whip")
	enemy._buffs.clear()
	var ally=load("res://scenes/enemies/ordinary_zombie.tscn").instantiate()
	var nested := Node3D.new()
	world.add_child(nested)
	nested.add_child(ally)
	ally.position=Vector3(5,0,0)
	ally.set_physics_process(false)
	check(is_equal_approx(enemy.walk_reference_speed,.32/(1.5*.65)),"V11 walk reference speed")
	ally.apply_inspire(15000,1.7,1.8)
	check(is_equal_approx(ally._buffs.speed_mul(),1.7) and is_equal_approx(ally._buffs.atk_mul(),1.8),"configured inspire multipliers consumed")
	ally._buffs.clear()
	enemy._start_howl()
	check(enemy._buffs.has("inspire") and ally._buffs.has("inspire"),"howl inspires enemy faction at action start")
	check(ally.contact_damage==20,"legacy ally consumes rally damage")
	enemy._start_howl()
	check(ally.contact_damage==20,"rally refresh does not multiply twice")
	check(enemy.combat_state == &"howl", "explicit howl state")
	ally._buffs.tick(15.1,ally)
	ally.get_node("ForemanInspiration")._process(0)
	check(ally.contact_damage==13,"rally expiration restores base damage")
	enemy._cancel_attack()
	enemy._buffs.clear()
	enemy.howl_remaining=30
	target.position=Vector3(0,0,10)
	var start: Vector3=enemy.global_position
	enemy.set_physics_process(true)
	for i in range(90):await physics_frame
	check(enemy.global_position.distance_to(start)>.5,"actual grounded chase moves")
	check(absf(enemy.global_position.y)<.15,"chase remains on floor")
	enemy.set_physics_process(false)
	var caves:=get_nodes_in_group("foreman_mine_caves")
	check(caves.size()==1,"one shared cave at safe floor point")
	if not caves.is_empty():
		var cave=caves[0]
		check(cave._buffs.has("statusImmune"),"cave has permanent status immunity")
		check(cave._spawn(false),"cave spawns original miner from bundled config")
		for child in world.get_children():
			if child.get_script()==load("res://scripts/dungeon_source_enemy.gd"):
				child.set_physics_process(false)
				child.queue_free()
		await process_frame
		await physics_frame
		check(cave._spawn(true),"cave spawns original lantern miner")
		for child in world.get_children():
			if child.get_script()==load("res://scripts/foreman_lantern.gd"):
				child.set_physics_process(false)
				child.queue_free()
		cave.take_damage(1000000)
		cave.queue_free()
		await process_frame
		enemy._physics_process(.6)
		check(get_nodes_in_group("foreman_mine_caves").is_empty(),"destroyed cave is not rebuilt")
	enemy._start_attack(Vector3.BACK)
	var before_kills:=kills
	enemy.take_damage(1000000)
	enemy.take_damage(1000000)
	check(kills==before_kills+1 and enemy._dead,"death notifies once")
	var hit_count: int=target.hits
	enemy._physics_process(1)
	check(target.hits==hit_count and enemy.action.is_empty(),"death cancels unfinished whip")
	enemy._physics_process(1.8)
	await process_frame
	check(not is_instance_valid(enemy),"death hold fade removes corpse")
	print("FOREMAN checks=",checks," failures=",failures)
	world.queue_free()
	await process_frame
	await process_frame
	quit(failures)
