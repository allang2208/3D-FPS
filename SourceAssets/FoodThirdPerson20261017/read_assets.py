"""Read current food animation tracks/metadata without mutating assets or running play."""
import json, hashlib
from pathlib import Path
import unreal as u
R=Path('D:/FPS3D/FPSGAME'); O=R/'SourceAssets/FoodThirdPerson20261017'
cfg=json.loads((R/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
mesh=u.load_asset(cfg['body_mesh']); ref=mesh.skeleton.get_reference_pose()
names=[str(n) for n in u.AnimPoseExtensions.get_bone_names(ref)]
def pack(t):return [*t.translation.to_tuple(),t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w,*t.scale3d.to_tuple()]
def disk(p):return R/'Content'/(p.split('.')[0][6:]+'.uasset')
def digest(p):return hashlib.sha256(disk(p).read_bytes()).hexdigest()
report={'mesh':mesh.get_path_name(),'mesh_sha256':digest(mesh.get_path_name()),'names':names,'clips':{}}
report['post_process']=str(mesh.get_editor_property('post_process_anim_blueprint'))
report['reference']=[pack(u.AnimPoseExtensions.get_bone_pose(ref,n,u.AnimPoseSpaces.LOCAL)) for n in names]
dm,status=u.GeometryScript_AssetUtils.copy_mesh_from_skeletal_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
Q=u.GeometryScript_MeshQueries;L=u.GeometryScript_List;W=u.GeometryScript_BoneWeights
_,ps,_=Q.get_all_vertex_positions(dm,False);ps=L.convert_vector_list_to_array(ps)
_,ts,_=Q.get_all_triangle_indices(dm,False);ts=L.convert_triangle_list_to_array(ts)
_,bones=W.get_all_bones_info(dm);bn={b.index:str(b.name) for b in bones};weights=[]
for i in range(len(ps)):
    _,ws,valid=W.get_vertex_bone_weights(dm,i);weights.append({bn[w.bone_index]:w.weight for w in ws if w.weight>0} if valid else {})
(O/'body_geometry.json').write_text(json.dumps({'positions':[list(p.to_tuple()) for p in ps],'triangles':[list(t.to_tuple()) for t in ts],'weights':weights},separators=(',',':')))
food_paths={'bread':'Bread20261003/SM_Bread','baguette_bread':'Baguette20261003/SM_Baguette',
 'roasted_chicken_leg':'ChickenLeg20261014/Roasted/SM_RoastedChickenLeg','roasted_lamb_ribs':'LambRibs20261014/Roasted/SM_RoastedLambRibs',
 'roasted_sausage':'Sausage20261014/Roasted/SM_RoastedSausage','roasted_large_lamb':'LargeLamb20261014/Roasted/SM_RoastedLargeLamb'}
foods={}
for key,path in food_paths.items():
    prop=u.load_asset('/Game/Items/Consumables/'+path)
    dm,status=u.GeometryScript_AssetUtils.copy_mesh_from_static_mesh(prop,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    _,ps,_=Q.get_all_vertex_positions(dm,False);_,ts,_=Q.get_all_triangle_indices(dm,False)
    foods[key]={'vertices':[list(p.to_tuple()) for p in L.convert_vector_list_to_array(ps)],'faces':[list(t.to_tuple()) for t in L.convert_triangle_list_to_array(ts)]}
(O/'food_geometries.json').write_text(json.dumps(foods,separators=(',',':')))
for key in ['Consume.EatBread','Consume.EatBaguette','Consume.EatLargeLamb']:
    asset=u.load_asset(cfg['clips'][key]); opt=u.AnimPoseEvaluationOptions();opt.optional_skeletal_mesh=mesh;opt.evaluation_type=u.AnimDataEvalType.COMPRESSED
    frames=[]; length=asset.get_play_length()
    for i in range(round(length*60)+1):
        pose=u.AnimPoseExtensions.get_anim_pose_at_time(asset,min(i/60,length),opt)
        frames.append([pack(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.LOCAL)) for n in names])
    report['clips'][key]={'asset':asset.get_path_name(),'sha256':digest(asset.get_path_name()),'rate':60,'duration':length,'markers':{str(m.marker_name):m.time for m in u.AnimationLibrary.get_animation_sync_markers(asset)},'frames':frames}
(O/'saved_clips_before.json').write_text(json.dumps(report,separators=(',',':')))
print('FOOD_CURRENT_ASSETS_READ',report['post_process'],[(k,len(v['frames'])) for k,v in report['clips'].items()])
