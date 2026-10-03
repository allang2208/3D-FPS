"""M09 authored full-body clips; background production, no previews or pose tests."""
import bpy,math,json
from pathlib import Path
from mathutils import Vector,Quaternion
ROOT=Path("D:/FPS3D/FPSGAME/SourceAssets/HangingBellM09Meshy20261003")
OUT=ROOT/"MotionV04"
for p in ["Authoring","Exports","Records"]: (OUT/p).mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/"RigV03/Authoring/M09_Rigged_v03.blend"))
rig=bpy.data.objects["M09_Rig_V03"];scene=bpy.context.scene;scene.render.fps=30
for p in rig.pose.bones:
 for c in list(p.constraints):p.constraints.remove(c)
rig.animation_data_clear()
# Runtime hand support applies after the clips. Bake editable FK body and organ motion.
names=[b.name for b in rig.data.bones if b.use_deform]
for p in rig.pose.bones:p.rotation_mode="QUATERNION"
def sm(x):
 x=max(0.,min(1.,x));return x*x*(3-2*x)
def env(t,a,b,c,d):return sm((t-a)/max(.001,b-a))*(1-sm((t-c)/max(.001,d-c)))
def rot(name,axis,degrees):
 p=rig.pose.bones.get(name)
 if not p:return
 local=rig.data.bones[name].matrix_local.to_3x3().inverted()@Vector(axis)
 p.rotation_quaternion=Quaternion(local.normalized(),math.radians(degrees))@p.rotation_quaternion
def leaf(side,layer,degrees,t):
 sign=1 if side=="L" else -1
 for k,f in [(1,.42),(2,.29),(3,.19),(4,.10)]:
  rot(f"membrane_{side}{layer}_{k:02d}",(0,1,0),sign*degrees*f)
  rot(f"membrane_{side}{layer}_{k:02d}",(1,0,0),math.sin(t*4-layer-k*.35)*min(1.3,abs(degrees)*.06+.4))
def curl(side,amount,small=False):
 for digit in range(1,6):
  for joint in range(1,4):rot(f"{'smallfinger' if small else 'hook'}_{side}_{digit:02d}_{joint:02d}",(1,0,0),amount*(.7 if digit==1 else 1.0))
roles={"Idle":(3.2,True),"Travel":(1.2,True),"SwingLeft":(2.3,False),"SwingRight":(2.3,False),
       "Resonance":(2.8,False),"Gaze":(3.,False),"Claw":(1.1,False),"Stagger":(1.4,False),"Death":(1.,False)}
receipt={}
for role,(length,loop) in roles.items():
 action=bpy.data.actions.new("A_M09_"+role);rig.animation_data_create();rig.animation_data.action=action
 frames=round(length*30);scene.frame_start=1;scene.frame_end=frames+1
 for frame in range(frames+1):
  t=frame/30;phase=2*math.pi*t/(length if loop else 3.2)
  for p in rig.pose.bones:p.location=(0,0,0);p.rotation_quaternion=(1,0,0,0);p.scale=(1,1,1)
  amplitude=1.2*math.sin(phase) if loop else .3*math.sin(t*2)
  rot("suspension",(0,1,0),amplitude);rot("spine_02",(1,0,0),.6*math.sin(phase+.6))
  for side in ["L","R"]:
   for layer in range(1,4):leaf(side,layer,1.2*math.sin(phase-layer*.35),t)
  if role=="Travel":
   rot("suspension",(0,1,0),2.0*math.sin(phase));rot("spine_02",(1,0,0),2*math.sin(phase*2))
   curl("L",-9*max(0,math.sin(phase)));curl("R",-9*max(0,-math.sin(phase)))
  elif role.startswith("Swing"):
   sign=1 if role=="SwingLeft" else -1
   angle=-15*sm(t/.70) if t<.70 else -15+41*sm((t-.70)/.36) if t<1.06 else 26*(1-sm((t-1.06)/1.24))
   rot("suspension",(0,1,0),angle*sign);rot("eye_crown",(0,1,0),-angle*.16*sign)
   for side in ["L","R"]:
    curl(side,18*env(t,0,.5,1.3,2.3),True)
    for layer in range(1,4):leaf(side,layer,-9*env(t,0,.6,1.25,2.3),t)
  elif role=="Resonance":
   for side in ["L","R"]:
    for layer,pulse in [(1,1.1),(2,1.45),(3,1.8)]:
     leaf(side,layer,47*env(t,.12,.95,pulse,2.8)+9*env(t,pulse-.10,pulse,pulse+.08,pulse+.32),t)
   rot("spine_01",(1,0,0),-5*env(t,0,.9,1.8,2.8))
  elif role=="Gaze":
   charge=env(t,0,.9,1.85,3)
   rot("crown_neck",(1,0,0),-7*charge)
   for side in ["L","R"]:rot(f"small_upperarm_{side}",(0,1,0),(1 if side=="L" else -1)*10*charge)
  elif role=="Claw":
   thrust=env(t,0,.35,.55,1.1)
   for side,sgn in [("L",1),("R",-1)]:
    rot("small_upperarm_"+side,(0,1,0),sgn*22*thrust)
    rot("small_forearm_"+side,(1,0,0),-34*thrust)
    rot("small_hand_"+side,(0,0,1),sgn*16*thrust)
    curl(side,-22*env(t,0,.28,.38,.62)+26*env(t,.32,.50,.67,1.1),True)
  elif role=="Stagger":
   hit=env(t,0,.18,.85,1.4)
   rot("suspension",(0,1,0),-12*hit);rot("spine_01",(1,0,0),9*hit)
   rot("big_upperarm_L",(0,1,0),-16*hit);rot("big_forearm_L",(1,0,0),30*hit);curl("L",-14*hit)
   for side in ["L","R"]:
    for layer in range(1,4):leaf(side,layer,9*math.sin(t*8-layer*.4)*hit,t)
  elif role=="Death":
   drop=sm(t/.6)
   rot("spine_01",(1,0,0),18*drop);rot("eye_crown",(0,1,0),15*drop)
   for side,delay,sgn in [("L",.18,1),("R",.34,-1)]:
    release=sm((t-delay)/.26)
    rot("big_upperarm_"+side,(0,1,0),-sgn*65*release)
    rot("big_forearm_"+side,(1,0,0),55*release);curl(side,-25*release)
    for layer in range(1,4):leaf(side,layer,-13*drop,t)
  for name in names:
   p=rig.pose.bones[name]
   p.keyframe_insert("location",frame=frame+1,group=name);p.keyframe_insert("rotation_quaternion",frame=frame+1,group=name);p.keyframe_insert("scale",frame=frame+1,group=name)
 action.use_fake_user=True;scene.frame_set(1)
 bpy.ops.object.select_all(action="DESELECT");rig.select_set(True);bpy.context.view_layer.objects.active=rig
 out=OUT/"Exports"/("A_M09_"+role+".fbx")
 bpy.ops.export_scene.fbx(filepath=str(out),use_selection=True,object_types={"ARMATURE"},
  apply_unit_scale=True,apply_scale_options="FBX_SCALE_UNITS",axis_forward="-Z",axis_up="Y",
  bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0,
  add_leaf_bones=False,use_armature_deform_only=True)
 receipt[role]={"file":str(out),"duration":length,"fps":30,"loop":loop,"source":"Original authored M09 movement; runtime hand IK provides contact"}
 print("M09_CLIP_SAVED",role,flush=True)
rig.animation_data.action=bpy.data.actions["A_M09_Idle"];scene.frame_start=1;scene.frame_end=97;scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/"Authoring/M09_Motion_v04.blend"),compress=True)
(OUT/"Records/motion_manifest.json").write_text(json.dumps(receipt,indent=2),encoding="utf8")
print("M09_MOTION_SAVED",len(receipt),flush=True)
