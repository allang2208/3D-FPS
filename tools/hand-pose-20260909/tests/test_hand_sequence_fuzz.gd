extends SceneTree
const OUT="E:/无尽轮回/3d/free-hands-20260908/"
var operations=0
var failures=[]
var trace=[]
func _initialize():call_deferred("run")
func snapshot(m):
 var values=[];var r=m._foregrip_rig.rig
 for b in r.get_bone_count():values.append(r.get_bone_global_pose(b))
 return values
func run():
 root.get_node("HUD").set_process(false)
 var args=OS.get_cmdline_user_args()
 for weapon in (["infima_ar","akm_classic","hk416","qbz191","m16","infima_handgun"] if args.is_empty() else [args[0]]):
  var m=load("res://scenes/weapons/"+weapon+".tscn").instantiate();root.add_child(m)
  var ref=load("res://scenes/weapons/"+weapon+".tscn").instantiate();root.add_child(ref)
  var hand=m.find_child("SK_FP_CH_Default_Cubic",true,false)
  if hand==null:hand=m.find_child("Infima_Standard_Arms",true,false)
  var mesh=hand.mesh;var clips=[]
  for clip in m.player.get_animation_list():
   if clip!="RESET" and not str(clip).begins_with("drum_"):clips.append(clip)
  for seed_value in [90801,90817,90831]:
   var rng=RandomNumberGenerator.new();rng.seed=seed_value
   var ads=0.0;var parts={}
   m.cancel_action();m.apply_gunsmith_parts(parts)
   for index in 1000:
    var command=rng.randi_range(0,9)
    var dt=[1.0/30,1.0/60,1.0/144][rng.randi_range(0,2)]
    var entry={"weapon":weapon,"seed":seed_value,"index":index,"command":command,"dt":dt}
    if command<4:
     var clip=clips[rng.randi_range(0,clips.size()-1)];entry.clip=clip
     m.play_action(clip);m.stop_action_audio()
    elif command==4:
     m.cancel_action();ads=0.0
     ref.apply_gunsmith_parts(parts);ref.cancel_action()
     var a=snapshot(m);var b=snapshot(ref)
     for bone in a.size():
      if (m._foregrip_rig.rig.global_basis*(a[bone].origin-b[bone].origin)).length()>.0002:failures.append("cancel retains old position "+str(bone))
      if a[bone].basis.orthonormalized().get_rotation_quaternion().angle_to(b[bone].basis.orthonormalized().get_rotation_quaternion())>.003:failures.append("cancel retains old rotation "+str(bone))
    elif command==5:ads=1.0-ads
    elif command==6:
     var before=snapshot(m);m.apply_gunsmith_parts(parts)
     if before!=snapshot(m):failures.append("same configuration mutates pose")
    elif command==7 and weapon!="infima_handgun":
     var grip=[false,true,"vertical","handstop","canted"][rng.randi_range(0,4)]
     parts={} if not grip else {"underbarrel":grip}
     if rng.randf()<.5:parts.magazine="large_drum"
     entry.parts=parts.duplicate();m.apply_gunsmith_parts(parts)
    elif command==8:parts={};m.apply_gunsmith_parts(parts)
    else:dt=.25
    trace.append(entry)
    if trace.size()>24:trace.pop_front()
    m.advance_pose(ads,dt)
    if hand.mesh!=mesh:failures.append("fitted hand replaced")
    for pose in snapshot(m):
     if not pose.origin.is_finite() or not pose.basis.is_finite():failures.append("invalid bone transform")
    var p=m._foregrip_pose
    if m._mounted_parts.has("underbarrel") and (p.action=="" or p.elapsed>=p.action_length):
     var r=m._foregrip_rig
     var distance=r.rig.to_global(r.rig.get_bone_global_pose(r.hand).origin).distance_to(m._part_point("underbarrel","HandTarget"))
     if distance>.001:failures.append("settled grip drift "+str(distance))
    operations+=1
    if index%20==0:await process_frame
    if not failures.is_empty():break
   if not failures.is_empty():break
  m.queue_free();ref.queue_free();await process_frame
  print("HAND_SEQUENCE_WEAPON ",weapon," operations=",operations," failures=",failures.size())
  if not failures.is_empty():break
 var file=FileAccess.open(OUT+"hand-sequence-fuzz"+("" if args.is_empty() else "-"+str(args[0]))+".json",FileAccess.WRITE)
 file.store_string(JSON.stringify({"operations":operations,"seeds":[90801,90817,90831],"failures":failures,"last_trace":trace},"  "));file.close()
 print("HAND_SEQUENCE_COMPLETE operations=",operations," failures=",failures.size())
 quit(0 if failures.is_empty() else 1)
