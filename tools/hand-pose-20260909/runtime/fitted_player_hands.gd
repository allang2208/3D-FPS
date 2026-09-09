extends RefCounted
## Mesh-only replacement. Each resource retains the target rig's bind table and sleeves.
const DIRECTORY="res://assets/models/player_hands/free_fitted_v1/"
const MODEL_IDS={
 "res://assets/models/infima/infima_ar.glb":"infima_ar",
 "res://assets/models/infima/infima_handgun.glb":"infima_handgun",
 "res://assets/models/akm_classic/akm_refined_v2.glb":"akm_classic",
 "res://assets/models/hk416/hk416.glb":"hk416",
 "res://assets/models/qbz191/qbz191.glb":"qbz191",
 "res://assets/models/m16/m16_modular_v2.glb":"m16",
}
static func apply(model:Node,source_path:String)->void:
 if not MODEL_IDS.has(source_path):return
 var mesh=load(DIRECTORY+MODEL_IDS[source_path]+".res") as ArrayMesh
 assert(mesh!=null,"Fitted hands resource missing: "+source_path)
 var node=model.find_child(str(mesh.get_meta("target_mesh")),true,false) as MeshInstance3D
 assert(node!=null and node.skin!=null,"Fitted hands target missing: "+source_path)
 var names:PackedStringArray=PackedStringArray(mesh.get_meta("target_bind_names"))
 assert(node.skin.get_bind_count()==names.size(),"Fitted hands bind count changed")
 var rig:Skeleton3D=node.get_node(node.skeleton)
 for j in names.size():
  var name_=str(node.skin.get_bind_name(j))
  if name_.is_empty():name_=rig.get_bone_name(node.skin.get_bind_bone(j))
  assert(name_==names[j],"Fitted hands bind order changed: "+name_)
 node.mesh=mesh
 node.set_meta("fitted_hands_version","free_fitted_v1")
