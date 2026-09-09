extends SceneTree
const OUT="E:/无尽轮回/3d/free-hands-20260908/"
var failures=[]
var cases=0
var max_position=0.0
var max_angle=0.0
func _initialize():call_deferred("run")
func duration(m,data,clip,drum):
 if clip in ["idle","aim"]:return .3
 if clip in ["reload","reload_empty"]:return (data.reload_time if clip=="reload" else data.empty_reload_time)*(1.75 if drum else 1.0)
 return m.player.get_animation(clip).length
func start(m,clip,length):
 m.play_action(clip,length);m.stop_action_audio()
func compare(m,reference,tag):
 var a=m._foregrip_rig.rig;var b=reference._foregrip_rig.rig
 var position=0.0;var angle=0.0
 for bone in a.get_bone_count():
  var x=a.get_bone_global_pose(bone);var y=b.get_bone_global_pose(bone)
  assert(x.origin.is_finite() and x.basis.is_finite(),tag)
  position=maxf(position,(a.global_basis*(x.origin-y.origin)).length())
  angle=maxf(angle,x.basis.orthonormalized().get_rotation_quaternion().angle_to(y.basis.orthonormalized().get_rotation_quaternion()))
 max_position=maxf(max_position,position);max_angle=maxf(max_angle,angle)
 if position>.0002 or angle>.003:
  failures.append({"case":tag,"position_m":position,"angle_rad":angle})
func run():
 root.get_node("HUD").set_process(false)
 var args=OS.get_cmdline_user_args()
 var weapons=["infima_ar","akm_classic","hk416","qbz191","m16","infima_handgun"]
 if not args.is_empty():weapons=[args[0]]
 for weapon in weapons:
  var m=load("res://scenes/weapons/"+weapon+".tscn").instantiate();root.add_child(m)
  var reference=load("res://scenes/weapons/"+weapon+".tscn").instantiate();root.add_child(reference)
  var data=load("res://weapon_data/"+weapon+".tres")
  var clips=[]
  for clip in m.player.get_animation_list():
   if clip!="RESET" and not str(clip).begins_with("drum_"):clips.append(clip)
  for grip in ([false] if weapon=="infima_handgun" else [false,true,"vertical","handstop","canted"]):
   for drum in ([false] if weapon=="infima_handgun" else [false,true]):
    var parts={} if not grip else {"underbarrel":grip}
    if drum:parts.magazine="large_drum"
    m.apply_gunsmith_parts(parts);reference.apply_gunsmith_parts(parts)
    for from in clips:
     var length=duration(m,data,from,drum)
     for fps in [30,60,144]:
      var dt=1.0/fps
      var times=[0.0,dt,maxf(0,length*.5-dt),length*.5,maxf(0,length-dt),length,length+dt]
      for time in times:
       for to in clips:
        var tag="%s %s drum=%s %s@%.6f -> %s fps=%d"%[weapon,grip,drum,from,time,to,fps]
        start(m,from,length);m.advance_pose(1.0 if from=="aim" else 0.0,time)
        start(reference,&"idle",.3);reference.advance_pose(0.0,.6)
        var next_length=duration(m,data,to,drum)
        start(m,to,next_length);start(reference,to,next_length)
        for step in [0.0,dt,dt*3,next_length+.3]:
         var ads=1.0 if to in ["aim","aim_fire"] else 0.0
         m.advance_pose(ads,step);reference.advance_pose(ads,step)
         compare(m,reference,tag+" step="+str(step))
        cases+=1
        if failures.size()>10:break
       if failures.size()>10:break
      if failures.size()>10:break
     if failures.size()>10:break
    print("INTERRUPTION_CONFIG ",weapon," ",grip," drum=",drum," cases=",cases," failures=",failures.size())
    await process_frame
    if failures.size()>10:break
   if failures.size()>10:break
  m.queue_free();reference.queue_free();await process_frame
  if failures.size()>10:break
 var f=FileAccess.open(OUT+"action-interruptions"+("-"+str(args[0]) if not args.is_empty() else "")+".json",FileAccess.WRITE)
 f.store_string(JSON.stringify({"cases":cases,"failures":failures,"max_position_m":max_position,"max_angle_rad":max_angle},"  "));f.close()
 print("ACTION_INTERRUPTION_COMPLETE cases=",cases," failures=",failures.size()," max_position_m=",max_position," max_angle_rad=",max_angle)
 quit(0 if failures.is_empty() else 1)
