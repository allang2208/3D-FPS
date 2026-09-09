extends SceneTree
## A hand on a separate IK branch must stay on the physical forearm tip.
func _initialize():call_deferred("run")
func run():
 root.get_node("HUD").set_process(false)
 var maximum=0.0;var cases=0;var failures=[]
 for weapon in ["hk416","qbz191"]:
  var m=load("res://scenes/weapons/"+weapon+".tscn").instantiate();root.add_child(m)
  var source=load("res://scenes/weapons/"+weapon+".tscn").instantiate();root.add_child(source)
  var data=load("res://weapon_data/"+weapon+".tres")
  for grip in [true,"vertical","handstop","canted"]:
   for drum in [false,true]:
    var parts={"underbarrel":grip}
    if drum:parts.magazine="large_drum"
    m.apply_gunsmith_parts(parts);source.apply_gunsmith_parts(parts)
    for clip in m.player.get_animation_list():
     if clip=="RESET" or str(clip).begins_with("drum_"):continue
     var length=m.player.get_animation(clip).length
     if clip in ["reload","reload_empty"]:length=(data.reload_time if clip=="reload" else data.empty_reload_time)*(1.75 if drum else 1.0)
     if clip not in ["idle","aim"]:m.play_action(clip,length);source.play_action(clip,length);m.stop_action_audio();source.stop_action_audio()
     var worst=0.0
     for frame in ceili((length+.1)*60):
      var ads=1.0 if clip in ["aim","aim_fire"] else 0.0
      m.advance_pose(ads,1.0/60);source.advance_pose(ads,1.0/60)
      var p=m._foregrip_rig;var s=source._foregrip_rig
      source._drum_hand.restore(s.rig);source._foregrip_pose.restore(s.rig)
      var local_tip=s.rig.get_bone_global_pose(s.lower).affine_inverse()*s.rig.get_bone_global_pose(s.hand).origin
      var tip=p.rig.to_global(p.rig.get_bone_global_pose(p.lower)*local_tip)
      var wrist=p.rig.to_global(p.rig.get_bone_global_pose(p.hand).origin)
      worst=maxf(worst,tip.distance_to(wrist))
     maximum=maxf(maximum,worst);cases+=1
     if worst>.0015:failures.append("%s %s drum=%s %s gap=%s"%[weapon,grip,drum,clip,worst])
  m.queue_free();source.queue_free();await process_frame
 for failure in failures:push_error(failure)
 print("HAND_CUFF_COMPLETE cases=",cases," failures=",failures.size()," max_gap_m=",maximum)
 quit(0 if failures.is_empty() else 1)
