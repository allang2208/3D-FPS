extends SceneTree
const OUT="E:/无尽轮回/3d/free-hands-20260908/"
var failures=[]
var cases=0
var release_cases=0
var max_unrelated_error=0.0
var max_repeat_error=0.0
var changes=[]
func _initialize():call_deferred("run")
func check(ok,message):
 if not ok and not message in failures:failures.append(message);push_error(message)
func snapshot(r):
 var a=[]
 for b in r.get_bone_count():a.append(r.get_bone_global_pose(b))
 return a
func spread(r,layer,side):
 var i=layer.chain(r,side,"index");var p=layer.chain(r,side,"pinky")
 var x=(r.get_bone_global_pose(i[0]).origin-r.get_bone_global_pose(p[0]).origin).normalized()
 return absf((r.global_basis*(r.get_bone_global_pose(i[1]).origin-r.get_bone_global_pose(p[1]).origin)).dot((r.global_basis*x).normalized()))
func run():
 root.get_node("HUD").set_process(false)
 for w in ["infima_ar","akm_classic","hk416","qbz191","m16","infima_handgun"]:
  var m=load("res://scenes/weapons/"+w+".tscn").instantiate();root.add_child(m)
  var ref=load("res://scenes/weapons/"+w+".tscn").instantiate();root.add_child(ref);ref._held_hand_pose.enabled=false
  var r=m._foregrip_rig.rig;var rr=ref._foregrip_rig.rig
  var edited=[]
  for side in ["l","r"]:
   for finger in ["index","middle","ring","pinky"]:
    if side=="r" and finger=="index":continue
    edited.append_array(m._held_hand_pose.chain(r,side,finger))
  for grip in ([false] if w=="infima_handgun" else [false,true,"vertical","handstop","canted"]):
   for drum in ([false] if w=="infima_handgun" else [false,true]):
    var parts={} if not grip else {"underbarrel":grip}
    if drum:parts.magazine="large_drum"
    m.apply_gunsmith_parts(parts);ref.apply_gunsmith_parts(parts)
    for ads in [0.0,.25,.5,.75,1.0]:
     m.cancel_action();ref.cancel_action();m.advance_pose(ads,.2);ref.advance_pose(ads,.2)
     var tag=w+" "+str(parts)+" ads="+str(ads)
     var before=snapshot(r)
     for b in r.get_bone_count():
      var ancestor=b
      while ancestor>=0 and ancestor not in edited:ancestor=r.get_bone_parent(ancestor)
      check(r.get_bone_pose_position(b).is_equal_approx(rr.get_bone_pose_position(b)),tag+" translated joint")
      if b not in edited:check(r.get_bone_pose_rotation(b).is_equal_approx(rr.get_bone_pose_rotation(b)),tag+" unrelated local rotation "+str(b))
      if ancestor<0:
       var error=(r.global_basis*(before[b].origin-rr.get_bone_global_pose(b).origin)).length();max_unrelated_error=maxf(max_unrelated_error,error)
       check(error<.00001 and r.get_bone_pose_rotation(b).is_equal_approx(rr.get_bone_pose_rotation(b)),tag+" unrelated bone "+r.get_bone_name(b))
     if grip:
      for finger in m._foregrip_rig.fingers.values():
       for b in finger:check(r.get_bone_pose_rotation(b).is_equal_approx(rr.get_bone_pose_rotation(b)),tag+" grip finger contact changed")
     for repeat_ in 24:m.advance_pose(ads,0.0)
     var after=snapshot(r)
     for b in r.get_bone_count():
      var error=(r.global_basis*(before[b].origin-after[b].origin)).length();max_repeat_error=maxf(max_repeat_error,error)
      check(error<.00001 and before[b].basis.is_equal_approx(after[b].basis),tag+" accumulating pose "+str(b))
     if ads==1.0 and not grip:
      changes.append({"weapon":w,"drum":drum,"left_knuckle_span_before_m":spread(rr,m._held_hand_pose,"l"),"left_knuckle_span_after_m":spread(r,m._held_hand_pose,"l")})
     cases+=1
    for action in m.player.get_animation_list():
     if action in ["RESET","idle","aim","fire","aim_fire"] or str(action).begins_with("drum_"):continue
     m.play_action(action);ref.play_action(action);m.stop_action_audio();ref.stop_action_audio()
     m.advance_pose(1.0,.15);ref.advance_pose(1.0,.15)
     # Both models run the same grip/drum solve; only the held-pose layer differs.
     for b in r.get_bone_count():check(r.get_bone_pose_rotation(b).is_equal_approx(rr.get_bone_pose_rotation(b)),w+" release "+str(action)+" changed bone "+str(b))
     release_cases+=1
  m.queue_free();ref.queue_free();await process_frame
  print("HELD_HAND_WEAPON ",w," cases=",cases," release=",release_cases," failures=",failures.size())
 var f=FileAccess.open(OUT+"ads-finger-tests.json",FileAccess.WRITE);f.store_string(JSON.stringify({"cases":cases,"release_cases":release_cases,"failures":failures,"max_unrelated_error_m":max_unrelated_error,"max_repeat_error_m":max_repeat_error,"spans":changes},"  "));f.close()
 print("HELD_HAND_POSE_COMPLETE cases=",cases," release=",release_cases," failures=",failures.size());quit(0 if failures.is_empty() else 1)
