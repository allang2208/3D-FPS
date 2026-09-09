extends SceneTree
## Exercise production reload retiming and post-animation contact, including
## the settled tail before ammunition becomes available and the first idle frames.
const Drum=preload("res://scripts/large_drum_reload.gd")
var failures:Array[String]=[]
var max_contact_error:=0.0
func _initialize():call_deferred("run")
func check(ok:bool,message:String):
 if not ok and not message in failures:failures.append(message);push_error(message)
func run():
 root.get_node("HUD").set_process(false)
 var cases=0
 for weapon in ["infima_ar","akm_classic","hk416","qbz191","m16"]:
  var data=load("res://weapon_data/"+weapon+".tres")
  var m=load("res://scenes/weapons/"+weapon+".tscn").instantiate();root.add_child(m);m.advance_pose(0,0)
  var source=load("res://scenes/weapons/"+weapon+".tscn").instantiate();root.add_child(source);source.advance_pose(0,0)
  for grip in [true,"vertical","handstop","canted"]:
   for drum in [false,true]:
    var parts={"underbarrel":grip};var reference_parts={}
    if drum:parts.magazine="large_drum";reference_parts.magazine="large_drum"
    m.apply_gunsmith_parts(parts);source.apply_gunsmith_parts(reference_parts)
    for clip in ["reload","reload_empty"]:
     for pair in [[30,.65],[60,1.0],[144,1.5]]:
      var fps:float=pair[0];var speed:float=pair[1]
      var base:float=data.reload_time if clip=="reload" else data.empty_reload_time
      var duration=base*(1.75 if drum else 1.0)/speed
      m.play_action(clip,duration);source.play_action(clip,duration);m.stop_action_audio();source.stop_action_audio()
      var p=m._foregrip_rig
      var start:float=p.return_times.x if clip=="reload" else p.return_times.y
      var end=minf(m.player.get_animation(clip).length-.06,start+.30)
      var catch_time=(Drum.output_time(end,base) if drum else end)/speed
      var tag="%s %s drum=%s %s fps=%s speed=%s"%[weapon,grip,drum,clip,fps,speed]
      var retreat:=0.0
      var previous_distance:float=-1.0
      for frame in ceili((duration+.2)*fps):
       var ads=1.0 if speed==1.5 else 0.0
       m.advance_pose(ads,1.0/fps);source.advance_pose(ads,1.0/fps)
       check(m.socket_position("SOCKET_Muzzle").distance_to(source.socket_position("SOCKET_Muzzle"))<.0001,tag+" muzzle")
       var t=(frame+1)/fps
       if str(grip)=="canted" and m._foregrip_pose.elapsed>=start and m._foregrip_pose.weight>0.0 and m._foregrip_pose.weight<1.0:
        var distance=p.rig.to_global(p.rig.get_bone_global_pose(p.hand).origin).distance_to(m._part_point("underbarrel","HandTarget"))
        if previous_distance>=0.0:retreat+=maxf(0.0,distance-previous_distance)
        previous_distance=distance
       if t>=catch_time+1.0/fps:
        var wrist=p.rig.to_global(p.rig.get_bone_global_pose(p.hand).origin)
        var error=wrist.distance_to(m._part_point("underbarrel","HandTarget"))
        max_contact_error=maxf(max_contact_error,error)
        # Match the existing 1 mm arm-reach/contact tolerance; preserve bone lengths.
        check(error<.001,tag+" settled wrist")
        check(m._drum_hand.correction_meters<.00001,tag+" clearance moved locked hand")
       if m._foregrip_pose.weight==0:
        for chain in p.fingers.values():
         for bone in chain:check(p.rig.get_bone_pose_rotation(bone).is_equal_approx(source._foregrip_rig.rig.get_bone_pose_rotation(bone)),tag+" released fingers")
      # Small shell clearance is allowed; a second hand-sized outward loop is not.
      if str(grip)=="canted":check(retreat<.08,tag+" excessive return detour "+str(retreat))
      cases+=1
  m.queue_free();source.queue_free();await process_frame
  print("REGRIP_CHECKED ",weapon," cases=",cases," failures=",failures.size())
 print("REGRIP_CONTACT_COMPLETE cases=",cases," failures=",failures.size()," max_contact_error_m=",max_contact_error);quit(0 if failures.is_empty() else 1)
