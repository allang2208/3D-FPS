"""Read the actual saved Jason body for scoped arm/torso penetration diagnosis."""
import unreal as u,json,hashlib
from pathlib import Path
O=Path('D:/FPS3D/FPSGAME/SourceAssets/LambTwoView20261017');R=O.parents[1]
cfg=json.loads((R/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'));asset=u.load_asset(cfg['body_mesh'])
dm,status=u.GeometryScript_AssetUtils.copy_mesh_from_skeletal_mesh(asset,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read Jason body')
Q=u.GeometryScript_MeshQueries;L=u.GeometryScript_List;W=u.GeometryScript_BoneWeights
_,ps,_=Q.get_all_vertex_positions(dm,False);ps=L.convert_vector_list_to_array(ps)
_,ts,_=Q.get_all_triangle_indices(dm,False);ts=L.convert_triangle_list_to_array(ts)
_,bones=W.get_all_bones_info(dm);names={b.index:str(b.name) for b in bones};weights=[]
for i in range(len(ps)):
    _,ws,valid=W.get_vertex_bone_weights(dm,i);weights.append({names[w.bone_index]:w.weight for w in ws if w.weight>0} if valid else {})
ref=asset.skeleton.get_reference_pose();order=[str(n) for n in u.AnimPoseExtensions.get_bone_names(ref)]
comp=u.new_object(u.SkeletalMeshComponent);comp.set_skeletal_mesh_asset(asset)
def pack(t):return [*t.translation.to_tuple(),t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w,*t.scale3d.to_tuple()]
rig=dict(mesh=asset.get_path_name(),skeleton=asset.skeleton.get_path_name(),names=order,parents=[order.index(str(comp.get_parent_bone(n))) if str(comp.get_parent_bone(n)) in order else -1 for n in order],reference=[pack(u.AnimPoseExtensions.get_bone_pose(ref,n,u.AnimPoseSpaces.LOCAL)) for n in order])
(O/'body_geometry.json').write_text(json.dumps(dict(asset=asset.get_path_name(),positions=[list(p.to_tuple()) for p in ps],triangles=[list(t.to_tuple()) for t in ts],weights=weights),separators=(',',':')))
(O/'body_rig.json').write_text(json.dumps(rig,separators=(',',':')))
print('LAMB_BODY_SOURCE_READ',len(ps),len(ts))
