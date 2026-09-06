extends SceneTree
class Target extends Node3D:
 var is_dead=false
 func take_damage(_amount,_kind="physical",_source=null):pass
var failures=0
var checks=0
func check(ok,message):
 checks+=1
 if not ok:failures+=1;push_error(message)
func _initialize():call_deferred("run")
func run():
 var world=Node3D.new();var local_hud=Control.new();local_hud.name="BackpackHud";world.add_child(local_hud);root.add_child(world);current_scene=world
 var ground=StaticBody3D.new();var shape=CollisionShape3D.new();var box=BoxShape3D.new();box.size=Vector3(40,.2,40);shape.shape=box;shape.position.y=-.1;ground.add_child(shape);world.add_child(ground)
 var enemy=load("res://scenes/enemies/foreman_zombie.tscn").instantiate()
 if not OS.get_cmdline_user_args().has("--formal"):
  enemy.get_node("Model").free();var model=load("res://tools/ai-gen/foreman-downstroke-v07-20260906/foreman-downstroke-v07.glb").instantiate();model.name="Model";enemy.add_child(model)
 world.add_child(enemy);enemy.set_physics_process(false);enemy._cave_requested=true;enemy.howl_remaining=999.;enemy.cooldown_remaining=999.
 var target=Target.new();world.add_child(target);target.position=Vector3(0,0,12);enemy.setup(target,func():pass)
 var sk=enemy._skeleton
 var max_turn=0.
 var max_slip=0.
 for clip in ["Idle","Walk","Attack","Death"]:
  var duration=enemy._ap.get_animation(clip).length
  var first=[];var previous=[]
  for tick in range(roundi(duration*60)+1):
   enemy._sync_pose(clip,minf(tick/60.,duration))
   var now=[]
   for i in sk.get_bone_count():
    var pose=sk.get_bone_global_pose(i);now.append(pose)
    if tick==0:first.append(pose)
    if tick>0 and not sk.get_bone_name(i).begins_with("whip."):
     var turn=previous[i].basis.get_rotation_quaternion().angle_to(pose.basis.get_rotation_quaternion())
     if turn>max_turn and turn>.5:print("JOINT_JUMP ",clip," t=",tick/60.," ",sk.get_bone_name(i)," ",turn)
     max_turn=maxf(max_turn,turn)
   if clip=="Walk" and tick>0:
    for side in range(2):
     var phase=fmod(tick/60./1.5+side*.5,1.)
     if phase>.06 and phase<.56:
      var index=sk.find_bone("foot.L" if side==0 else "foot.R")
      max_slip=maxf(max_slip,absf((now[index].origin.z-previous[index].origin.z)*60.+.40/(1.5*.62)))
   previous=now
  if clip in ["Idle","Walk"]:
   var error=0.
   for i in sk.get_bone_count():error=maxf(error,first[i].origin.distance_to(previous[i].origin));error=maxf(error,first[i].basis.get_rotation_quaternion().angle_to(previous[i].basis.get_rotation_quaternion()))
   check(error<.001,clip+" closed loop")
 check(max_slip<.06,"imported stance speed matches movement")
 check(max_turn<.5,"body joint step under 0.5 rad at 60Hz")
 enemy._sync_pose("Walk",.37)
 var before=sk.get_bone_global_pose(sk.find_bone("hand.R"))
 enemy._start_attack(Vector3.BACK)
 check(before.origin.distance_to(sk.get_bone_global_pose(sk.find_bone("hand.R")).origin)<.001,"attack carries visible previous pose")
 enemy._physics_process(.15)
 check(is_equal_approx(enemy.attack_elapsed,.15) and enemy._transition_from.is_empty(),"blend does not delay attack clock")
 enemy._cancel_attack();enemy.cooldown_remaining=999.;enemy.howl_remaining=999.
 enemy.set_physics_process(true)
 var start=enemy.position
 for i in range(90):await physics_frame
 enemy.set_physics_process(false)
 var moved=Vector2(enemy.position.x-start.x,enemy.position.z-start.z).length()
 check(moved>.8 and moved<1.1 and absf(enemy.position.y)<.05,"actual 0.65m/s chase grounded")
 enemy._sync_pose("Attack",.62)
 before=sk.get_bone_global_pose(sk.find_bone("hand.L"))
 enemy._die()
 check(before.origin.distance_to(sk.get_bone_global_pose(sk.find_bone("hand.L")).origin)<.001,"death preserves struck arm pose at start")
 print("FOREMAN_MOTION checks=",checks," failures=",failures," max_joint_step=",max_turn," moved_m=",moved," stance_speed_error=",max_slip)
 world.queue_free();await process_frame;await process_frame;quit(0 if failures==0 else 1)
