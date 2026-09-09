extends SceneTree
const OUT="E:/无尽轮回/3d/free-hands-20260908/"
const IDS=["fps_akm","fps_akm_classic","fps_hk416","fps_qbz191","fps_m16","fps_p9"]
var hud
var gun
var cases=0
var frame_checks=0
var rejected=0
var failures=[]
var tag=""
func _initialize():call_deferred("run")
func check(ok:bool,label:String):
 if not ok:
  if failures.size()<30:failures.append(tag+" "+label)
func validate():
 var m=gun._model
 check(is_instance_valid(m) and m.visible,"active model missing")
 var hand=m.find_child("SK_FP_CH_Default_Cubic",true,false)
 if hand==null:hand=m.find_child("Infima_Standard_Arms",true,false)
 check(hand!=null and hand.get_meta("fitted_hands_version","")=="free_fitted_v1","fitted mesh lost")
 var r=m._foregrip_rig.rig
 for b in r.get_bone_count():
  var pose=r.get_bone_global_pose(b)
  check(pose.origin.is_finite() and pose.basis.is_finite(),"invalid bone")
 if is_instance_valid(gun._stowed_model):check(not gun._stowed_model.visible and gun._stowed_model.process_mode==Node.PROCESS_MODE_DISABLED,"stowed model active")
 frame_checks+=1
func tick(dt:float):
 gun._physics_process(dt);gun._process(dt);gun._model.stop_action_audio();validate()
func advance(seconds:float,dt:float):
 var remaining=seconds
 while remaining>0.000001:
  var step=minf(dt,remaining);tick(step);remaining-=step
func settle(dt:float):
 # Empty magazines legitimately start automatic reload after equipment ends.
 for pass_index in 4:
  advance(maxf(gun._equip_t,gun._reload_t)+.15,dt)
  if gun._equip_t<=0 and gun._reload_t<=0:return
 check(false,"automatic equip/reload chain failed to settle")
func select(slot:String):
 hud._active_weapon_slot=slot;hud._applied_weapon_instance="";hud._sync_equipped_weapon();gun._model.stop_action_audio()
func parts(grip,drum,pistol):
 var result={}
 if not pistol:
  if grip:result.underbarrel=grip
  if drum:result.magazine="large_drum"
 return result
func run():
 assert(OS.has_environment("INVENTORY_SAVE_PATH"))
 hud=root.get_node("HUD");hud.set_process(false);hud._ensure_built()
 hud.backpack.slots.fill(null)
 for key in hud.equipment.slots:hud.equipment.slots[key]=null
 var world=Node3D.new();root.add_child(world)
 var camera=Camera3D.new();world.add_child(camera)
 gun=preload("res://scripts/gun.gd").new();camera.add_child(gun);gun.set_process(false);gun.set_physics_process(false)
 hud._bound_gun=gun
 var args=OS.get_cmdline_user_args()
 var source_ids=IDS if args.is_empty() else [args[0]]
 for from_id in source_ids:
  for to_id in IDS:
   for grip in [false,true,"vertical","handstop","canted"]:
    for drum in [false,true]:
     if from_id=="fps_p9" and to_id=="fps_p9" and (grip or drum):continue
     var a=hud.item_db.create_instance(from_id);var b=hud.item_db.create_instance(to_id)
     assert(not a.is_empty() and not b.is_empty())
     a.gunsmith_parts=parts(grip,drum,from_id=="fps_p9");b.gunsmith_parts=parts(grip,drum,to_id=="fps_p9")
     hud.equipment.slots.weapon=a;hud.equipment.slots.weapon2=b
     select("weapon");settle(1.0/60)
     for fps in [30,60,144]:
      var dt=1.0/fps
      for action in ["reload","reload_empty","equip"]:
       for phase in [0.0,.01,.25,.5,.9,.999,1.001]:
        tag="%s -> %s %s drum=%s %s phase=%s fps=%s"%[from_id,to_id,grip,drum,action,phase,fps]
        select("weapon");settle(dt)
        gun.ammo=0 if action=="reload_empty" else 1;gun.reserve=200
        if action=="equip":gun.play_equip()
        else:gun._start_reload()
        var length=maxf(gun._equip_t,gun._reload_t)
        advance(length*phase,dt)
        var before=Vector2i(gun.ammo,gun.reserve)
        var old_model=gun._model
        var old_data=gun.data
        var blocked=gun._reload_t>0 or gun._equip_t>0 or load(str(b.weapon_data))==gun.data
        # Direct requests are rejected while busy, without resetting the action.
        if blocked:
         check(not gun.switch_weapon(load(str(b.weapon_data))),"direct request should reject")
         check(gun._model==old_model and gun.data==old_data,"rejected switch mutated identity")
         rejected+=1
        # The real HUD entry cancels ownership before switching, even while busy.
        check(hud.cycle_inventory_weapon(),"HUD switch refused")
        check(hud._displayed_weapon_id==str(b.instance_id),"wrong target instance")
        validate()
        # Rapid A-B-A-B, including equipment's first frame; no timer overrides.
        for repeat in 3:
         check(hud.cycle_inventory_weapon(),"rapid cycle refused");validate();tick(dt)
        check(hud._displayed_weapon_id==str(a.instance_id),"source instance not restored")
        check(Vector2i(gun.ammo,gun.reserve)==before,"interrupted reload changed source ammunition")
        settle(dt)
        var m=gun._model
        if m._mounted_parts.has("underbarrel"):
         var p=m._foregrip_rig
         var error=p.rig.to_global(p.rig.get_bone_global_pose(p.hand).origin).distance_to(m._part_point("underbarrel","HandTarget"))
         check(error<.001,"return grip not settled error=%s action=%s elapsed=%s weight=%s equip=%s"%[error,m._foregrip_pose.action,m._foregrip_pose.elapsed,m._foregrip_pose.weight,gun._equip_t])
        cases+=1
        if not failures.is_empty():break
       if not failures.is_empty():break
      if not failures.is_empty():break
     await process_frame
     if not failures.is_empty():break
    if not failures.is_empty():break
   print("WEAPON_INTERRUPT_PAIR ",from_id," -> ",to_id," cases=",cases," failures=",failures.size())
   if not failures.is_empty():break
  if not failures.is_empty():break
 var f=FileAccess.open(OUT+"weapon-interruptions"+("-"+str(args[0]) if not args.is_empty() else "")+".json",FileAccess.WRITE)
 f.store_string(JSON.stringify({"cases":cases,"frame_checks":frame_checks,"rejected_direct_requests":rejected,"failures":failures},"  "));f.close()
 print("WEAPON_INTERRUPTION_COMPLETE cases=",cases," frame_checks=",frame_checks," failures=",failures.size())
 for failure in failures:push_error(failure)
 hud._bound_gun=null;world.queue_free();await process_frame
 quit(0 if failures.is_empty() else 1)
