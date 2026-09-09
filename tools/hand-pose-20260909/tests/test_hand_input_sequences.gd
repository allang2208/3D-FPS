extends "res://tests/test_hand_weapon_interruptions.gd"
var shots=0
func mouse(button:int,pressed:bool):
 var e=InputEventMouseButton.new();e.button_index=button;e.pressed=pressed;Input.parse_input_event(e)
func run():
 root.size=Vector2i(960,640)
 hud=root.get_node("HUD");hud.set_process(false);hud._ensure_built()
 for child in hud.get_children():
  if child is CanvasLayer:child.visible=false
 hud.backpack.slots.fill(null)
 for key in hud.equipment.slots:hud.equipment.slots[key]=null
 var world=Node3D.new();root.add_child(world);current_scene=world
 var camera=Camera3D.new();world.add_child(camera);camera.make_current()
 gun=preload("res://scripts/gun.gd").new();camera.add_child(gun);gun.set_process(false);gun.set_physics_process(false);hud._bound_gun=gun
 Input.mouse_mode=Input.MOUSE_MODE_CAPTURED
 print("INPUT_TEST_MOUSE_MODE ",Input.mouse_mode)
 assert(Input.mouse_mode==Input.MOUSE_MODE_CAPTURED,"This input test needs the graphical backend; headless cannot capture mouse input")
 var commands=0;var trace=[]
 for index in IDS.size():
  var a=hud.item_db.create_instance(IDS[index]);var b=hud.item_db.create_instance(IDS[(index+1)%IDS.size()])
  a.gunsmith_parts=parts("canted",true,index==5);b.gunsmith_parts=parts("vertical",true,(index+1)%6==5)
  hud.equipment.slots.weapon=a;hud.equipment.slots.weapon2=b;select("weapon")
  gun.reserve=200;settle(1.0/60)
  for seed_value in [90901,90919,90937]:
   var rng=RandomNumberGenerator.new();rng.seed=seed_value+index
   var left=false;var right=false
   for frame in 1600:
    # Include playable gaps as well as adversarial button spam, so firing is
    # exercised instead of every trigger request being blocked by equipment.
    if frame%80==0:
     left=false;right=false;mouse(MOUSE_BUTTON_LEFT,false);mouse(MOUSE_BUTTON_RIGHT,false)
     gun.building_input_blocked=false;hud._sync_equipped_weapon();settle(1.0/60)
     mouse(MOUSE_BUTTON_RIGHT,true);mouse(MOUSE_BUTTON_LEFT,true)
     for shot_frame in 24:
      var ammo_before=gun.ammo
      tick(1.0/60)
      shots+=maxi(0,ammo_before-gun.ammo)
     mouse(MOUSE_BUTTON_LEFT,false);mouse(MOUSE_BUTTON_RIGHT,false)
    var command=rng.randi_range(0,12)
    var dt=[1.0/30,1.0/60,1.0/144][rng.randi_range(0,2)]
    tag="input %s seed=%s frame=%s cmd=%s"%[IDS[index],seed_value,frame,command]
    trace.append(tag)
    if trace.size()>24:trace.pop_front()
    match command:
     0:left=not left;mouse(MOUSE_BUTTON_LEFT,left)
     1:right=not right;mouse(MOUSE_BUTTON_RIGHT,right)
     2:gun._start_reload()
     3:hud.cycle_inventory_weapon()
     4:
      if gun.inventory_active:gun.set_inventory_active(false)
      else:hud._sync_equipped_weapon()
     5:
      var item=hud.equipment.get_item(hud._active_weapon_slot)
      item.gunsmith_parts=parts([false,true,"vertical","handstop","canted"][rng.randi_range(0,4)],rng.randf()<.5,str(item.weapon_data).ends_with("infima_handgun.tres"))
      hud._applied_weapon_instance="";hud._sync_equipped_weapon()
     6:gun.cycle_fire_mode()
     7:gun.building_input_blocked=not gun.building_input_blocked
     8:
      for repeat in 3:hud.cycle_inventory_weapon()
    var old_ammo=gun.ammo;var busy=gun._equip_t>dt or gun._reload_t>dt or not gun.inventory_active or gun.building_input_blocked
    gun._physics_process(dt);gun._process(dt);gun._model.stop_action_audio()
    if gun.ammo<old_ammo:shots+=old_ammo-gun.ammo
    if busy and gun._equip_t>0:check(gun.ammo==old_ammo,"shot during equipment")
    if gun.inventory_active:validate()
    else:check(not gun.visible and gun._reload_t<=0 and gun._equip_t<=0,"hidden gun retained active action")
    check(gun.ammo>=0 and gun.ammo<=gun._effective_mag(),"invalid ammunition")
    commands+=1
    if frame%20==0:await process_frame
    if not failures.is_empty():break
   mouse(MOUSE_BUTTON_LEFT,false);mouse(MOUSE_BUTTON_RIGHT,false);gun.building_input_blocked=false;hud._sync_equipped_weapon();settle(1.0/60)
   if not failures.is_empty():break
  print("HAND_INPUT_WEAPON ",IDS[index]," commands=",commands," shots=",shots," failures=",failures.size())
  if not failures.is_empty():break
 check(shots>0,"firing inputs were never exercised")
 var file=FileAccess.open(OUT+"hand-input-sequences.json",FileAccess.WRITE)
 file.store_string(JSON.stringify({"commands":commands,"shots":shots,"failures":failures,"last_trace":trace,"seeds":[90901,90919,90937]},"  "));file.close()
 print("HAND_INPUT_COMPLETE commands=",commands," shots=",shots," failures=",failures.size())
 hud._bound_gun=null;world.queue_free();await process_frame;quit(0 if failures.is_empty() else 1)
