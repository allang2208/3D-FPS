extends RefCounted
## Maps the shared grip pose to each existing arm rig without replacing source animations.
var rig: Skeleton3D
var upper: int
var lower: int
var hand: int
var fingers := {}
var wrist := preload("res://scripts/foregrip_finger_pose.gd").WRIST
var separate_hand := false
var equip_return := Vector2(1.02,1.38)
var return_times := Vector2(1.85,2.15)
func setup(model: Node) -> void:
 # Setup runs again on actions/remounts: always calibrate from canonical rest data.
 wrist=preload("res://scripts/foregrip_finger_pose.gd").WRIST
 equip_return=Vector2(1.02,1.38)
 rig=null;fingers.clear();separate_hand=false;return_times=Vector2(1.85,2.15)
 for r in model.find_children("*","Skeleton3D",true,false):
  if r.find_bone("hand_l")>=0:
   rig=r;upper=r.find_bone("upperarm_l");lower=r.find_bone("lowerarm_l");hand=r.find_bone("hand_l")
   for f in preload("res://scripts/foregrip_finger_pose.gd").CONTACTS:
    fingers[f]=[r.find_bone(f+"_01_l"),r.find_bone(f+"_02_l"),r.find_bone(f+"_03_l")]
   return
  if r.find_bone("mixamorig2_LeftHand")>=0:
   rig=r;upper=r.find_bone("mixamorig2_LeftArm");lower=r.find_bone("mixamorig2_LeftForeArm");hand=r.find_bone("mixamorig2_LeftHand");separate_hand=true;equip_return=Vector2(.39,.55);return_times=Vector2(1.72,2.40)
   for f in preload("res://scripts/foregrip_finger_pose.gd").CONTACTS:
    fingers[f]=[]
    for j in 3:fingers[f].append(r.find_bone("mixamorig2_LeftHand"+f.capitalize()+str(j+1)))
  elif r.find_bone("L_wrist")>=0:
   rig=r;upper=r.find_bone("L_arm");lower=r.find_bone("L_elbow");hand=r.find_bone("L_wrist");equip_return=Vector2(.78,1.04);return_times=Vector2(1.90,2.10)
   for f in preload("res://scripts/foregrip_finger_pose.gd").CONTACTS:
    fingers[f]=[]
    for j in 3:fingers[f].append(r.find_bone("L_"+("point" if f=="index" else "pink" if f=="pinky" else f)+str(j+1)))
 if rig==null:return
 for chain in fingers.values():
  for b in chain:assert(b>=0)
 var source=load("res://assets/models/infima/infima_ar.glb").instantiate()
 var canonical:Skeleton3D=source.find_child("Skeleton3D",true,false)
 var canonical_hand=canonical.find_bone("hand_l")
 var ci=relative(canonical,canonical_hand,canonical.find_bone("index_01_l"))
 var cm=relative(canonical,canonical_hand,canonical.find_bone("middle_01_l"))
 var cp=relative(canonical,canonical_hand,canonical.find_bone("pinky_01_l"))
 var ti=relative(rig,hand,fingers.index[0]);var tm=relative(rig,hand,fingers.middle[0]);var tp=relative(rig,hand,fingers.pinky[0])
 wrist.basis=wrist.basis*anatomy(ci,cm,cp)*anatomy(ti,tm,tp).inverse()
 var source_space=Transform3D.IDENTITY
 var ancestor:Node=canonical
 while ancestor!=null:
  if ancestor is Node3D:source_space=ancestor.transform*source_space
  ancestor=ancestor.get_parent()
 var canonical_scale=source_space.basis.get_scale().x*canonical.get_bone_global_rest(canonical_hand).basis.get_scale().x
 var rig_in_model=model.global_transform.affine_inverse()*rig.global_transform
 var target_scale=rig_in_model.basis.get_scale().x*rig.get_bone_global_rest(hand).basis.get_scale().x
 wrist.origin+=preload("res://scripts/foregrip_finger_pose.gd").WRIST.basis*cm*canonical_scale-wrist.basis*tm*target_scale
 if not separate_hand:
  var before=wrist.basis
  wrist.basis=Basis(Vector3.RIGHT,.20)*wrist.basis
  wrist.origin+=(before*tm-wrist.basis*tm)*target_scale
  wrist.origin.z-=.006
 source.free()
static func relative(r:Skeleton3D,h:int,b:int)->Vector3:
 return r.get_bone_global_rest(h).affine_inverse()*r.get_bone_global_rest(b).origin
static func anatomy(i:Vector3,m:Vector3,p:Vector3)->Basis:
 var y=m.normalized();var x=(i-p).normalized();x=(x-y*x.dot(y)).normalized();return Basis(x,y,x.cross(y))
