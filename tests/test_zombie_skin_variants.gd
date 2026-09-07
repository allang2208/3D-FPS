extends SceneTree
var failures:=0
var kills:=0
class Target extends Node3D:
 var is_dead:=false
 func take_damage(_d:int)->void:pass
func _initialize()->void:call_deferred("run")
func check(value:bool,label:String)->void:
 if not value:failures+=1
 print("SKIN ",label," ", "PASS" if value else "FAIL")
func run()->void:
 var world:=Node3D.new()
 root.add_child(world);current_scene=world
 var target:=Target.new();world.add_child(target)
 var rows:=[[ "ordinary_zombie",120,13,"modern"],["miner_workwear_zombie",160,16,"miner"],["runner_zombie",90,11,"runner"]]
 seed(9072026)
 for row in rows:
  var scene:PackedScene=load("res://scenes/enemies/%s.tscn"%row[0])
  var originals:Array=[]
  var seen:={}
  for choice in [0,1]:
   var z=scene.instantiate()
   var model:Node3D=z.get_node("Model")
   var player:AnimationPlayer=model.find_child("AnimationPlayer",true,false)
   var animation:Animation=player.get_animation("Walk")
   var stats:Array=[z.max_hp,z.chase_speed,z.wander_speed,z.contact_damage,z.attack_cd,z.physical_defense]
   z.appearance_choice=choice
   world.add_child(z);z.set_physics_process(false)
   z.setup(target,func():kills+=1)
   check(z.chosen_appearance==choice,row[0]+" selected_"+str(choice))
   check(z._model==model and z._ap.get_animation("Walk")==animation,row[0]+" original_model_animation")
   check(stats==[z.max_hp,z.chase_speed,z.wander_speed,z.contact_damage,z.attack_cd,z.physical_defense],row[0]+" unchanged_stats")
   check(z._hp==row[1] and z.contact_damage==row[2],row[0]+" original_identity")
   check(z._skeleton.get_bone_count()==31 and z._head_bone>=0,row[0]+" skeleton_head_hitbox")
   if choice==1:
    check(z._mat.albedo_texture==load("res://assets/models/zombie_skin_variants/%s_albedo.png"%row[3]),row[0]+" variant_texture")
   originals.append(z)
  check(originals[0]._mat!=originals[1]._mat,row[0]+" isolated_flash_material")
  originals[1]._mat.emission_enabled=true
  check(not originals[0]._mat.emission_enabled,row[0]+" no_shared_flash")
  var selected:int=originals[1].chosen_appearance
  originals[1].setup(target,func():kills+=1)
  check(originals[1].chosen_appearance==selected,row[0]+" no_reroll")
  var previous_kills:=kills
  originals[1].take_damage(100000,"magic")
  originals[1].take_damage(100000,"magic")
  check(kills==previous_kills+1,row[0]+" kill_once")
  originals[1]._physics_process(originals[1].death_duration+originals[1].corpse_hold+.01)
  check(originals[1].is_queued_for_deletion(),row[0]+" corpse_cleanup")
  originals[0].free()
  for i in 24:
   var z=scene.instantiate()
   world.add_child(z);z.set_physics_process(false)
   seen[z.chosen_appearance]=true
   z.free()
  check(seen.has(0) and seen.has(1) and seen.size()==2,row[0]+" random_both_appearances")
 # Actual dungeon entry changes script before adding the ordinary zombie to the tree.
 var dungeon=load("res://scenes/enemies/ordinary_zombie.tscn").instantiate()
 dungeon.set_script(load("res://scripts/dungeon_zombie.gd"))
 dungeon.appearance_choice=1
 world.add_child(dungeon);dungeon.set_physics_process(false)
 check(dungeon.chosen_appearance==1 and dungeon._mat.albedo_texture==load("res://assets/models/zombie_skin_variants/modern_albedo.png"),"dungeon_script_swap_inherits_skin")
 dungeon.free()
 print("ZOMBIE_SKIN_INTEGRATION_COMPLETE failures=",failures)
 quit(1 if failures else 0)
