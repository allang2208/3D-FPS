extends SceneTree
const OUT="E:/无尽轮回/3d/free-hands-20260908/"
func _initialize():call_deferred("run")
func matrix(t:Transform3D):return [[t.basis.x.x,t.basis.y.x,t.basis.z.x,t.origin.x],[t.basis.x.y,t.basis.y.y,t.basis.z.y,t.origin.y],[t.basis.x.z,t.basis.y.z,t.basis.z.z,t.origin.z],[0,0,0,1]]
func semantic(r:Skeleton3D,s:String,f:String="",j:int=0)->String:
 if r.find_bone("hand_"+s)>=0:return "hand_"+s if f.is_empty() else "%s_%02d_%s"%[f,j,s]
 if r.find_bone("mixamorig2_LeftHand")>=0:return "mixamorig2_"+("Left" if s=="l" else "Right")+"Hand"+("" if f.is_empty() else f.capitalize()+str(j))
 return s.to_upper()+"_"+("wrist" if f.is_empty() else ("point" if f=="index" else "pink" if f=="pinky" else f)+str(j))
func run():
 root.get_node("HUD").set_process(false)
 var all={}
 for weapon in ["infima_ar","akm_classic","hk416","qbz191","m16","infima_handgun"]:
  var m=load("res://scenes/weapons/"+weapon+".tscn").instantiate();m.fitted_hands_enabled=false;root.add_child(m);m.advance_pose(0,0)
  var n=m.find_child("SK_FP_CH_Default_Cubic",true,false)
  if n==null:n=m.find_child("Infima_Standard_Arms",true,false)
  var r:Skeleton3D=n.get_node(n.skeleton);var rests={};var mapping={};var bind_names=[]
  for b in n.skin.get_bind_count():
   var name_=str(n.skin.get_bind_name(b));if name_.is_empty():name_=r.get_bone_name(n.skin.get_bind_bone(b))
   bind_names.append(name_)
  for side in ["l","r"]:
   var chain=["hand"]
   for f in ["thumb","index","middle","ring","pinky"]:
    for j in range(1,4):chain.append("%s_%02d"%[f,j])
   for key in chain:
    var name_=semantic(r,side) if key=="hand" else semantic(r,side,key.split("_")[0],int(key.split("_")[1]))
    var b=r.find_bone(name_);assert(b>=0,name_)
    var p=(r.global_transform*r.get_bone_global_rest(b)).origin
    rests[key+"_"+side]=[p.x,p.y,p.z];mapping[key+"_"+side]=bind_names.find(name_);assert(mapping[key+"_"+side]>=0)
  var b0=r.find_bone(bind_names[0]);var space=r.global_transform*r.get_bone_global_rest(b0)*n.skin.get_bind_pose(0)
  var held={}
  for key in mapping:
   var j=int(mapping[key]);held[key]=matrix(r.global_transform*r.get_bone_global_pose(r.find_bone(bind_names[j]))*n.skin.get_bind_pose(j)*space.affine_inverse())
  all[weapon]={"rests":rests,"mapping":mapping,"bind_names":bind_names,"mesh":str(n.name),"space":matrix(space),"inverse_space":matrix(space.affine_inverse()),"held":held}
  print("EXPORT_RIG ",weapon," ",n.name," ",space)
  m.queue_free();await process_frame
 var f=FileAccess.open(OUT+"hand-rigs.json",FileAccess.WRITE);f.store_string(JSON.stringify(all,"  "));f.close();print("HAND_RIGS_COMPLETE");quit()
