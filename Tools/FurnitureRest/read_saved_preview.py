"""Read saved rest animations and actual body/furniture geometry; never save UE packages."""
import json,os
from pathlib import Path
import unreal as u
ROOT=Path('D:/FPS3D/FPSGAME');OUT=ROOT/'SourceAssets/FurnitureRest20261022/RefineV2/ReviewSaved'
OUT=Path(os.environ.get('FURNITURE_REVIEW_OUT',str(OUT)))
OUT.mkdir(parents=True,exist_ok=True)
cfg=json.loads((ROOT/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
profiles=json.loads((ROOT/'Content/ColdSteelData/furniture_rest.json').read_text(encoding='utf-8-sig'))
mesh=u.load_asset(cfg['body_mesh']);ref=mesh.skeleton.get_reference_pose()
names=[str(n) for n in u.AnimPoseExtensions.get_bone_names(ref)]
comp=u.new_object(u.SkeletalMeshComponent);comp.set_skeletal_mesh_asset(mesh)
parents=[names.index(str(comp.get_parent_bone(n))) if str(comp.get_parent_bone(n)) in names else -1 for n in names]
def pack(t):return [t.translation.x,t.translation.y,t.translation.z,t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w,t.scale3d.x,t.scale3d.y,t.scale3d.z]
rig={'names':names,'parents':parents,'reference':[pack(u.AnimPoseExtensions.get_bone_pose(ref,n,u.AnimPoseSpaces.LOCAL)) for n in names],'clips':{},'mesh':mesh.get_path_name()}
opt=u.AnimPoseEvaluationOptions();opt.optional_skeletal_mesh=mesh;opt.evaluation_type=u.AnimDataEvalType.COMPRESSED
source_opt=u.AnimPoseEvaluationOptions();source_opt.optional_skeletal_mesh=mesh;source_opt.evaluation_type=u.AnimDataEvalType.SOURCE
for role,path in cfg['clips'].items():
 if not role.startswith(os.environ.get('FURNITURE_ROLE_PREFIX','Rest.')):continue
 clip=u.load_asset(path)
 if not clip or clip.get_editor_property('skeleton')!=mesh.skeleton:raise RuntimeError('Rest clip skeleton mismatch '+role)
 length=clip.get_play_length();frames=[];count=round(length*15)+1
 for i in range(count):
  pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,length*i/(count-1),opt)
  frames.append([pack(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.LOCAL)) for n in names])
 endpoints=[]
 for t in (0,length):
  pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,t,source_opt)
  endpoints.append([pack(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.LOCAL)) for n in names])
 rig['clips'][role]={'duration':length,'frames':frames,'asset':path,'source_endpoints':endpoints,'evaluation':'compressed'}
(OUT/'saved_poses.json').write_text(json.dumps(rig,separators=(',',':')))
G,Q,B,L=u.GeometryScript_AssetUtils,u.GeometryScript_MeshQueries,u.GeometryScript_BoneWeights,u.GeometryScript_List
def xyz(v):return [v.x,v.y,v.z]
def geometry(asset,skeletal=False):
 copier=G.copy_mesh_from_skeletal_mesh if skeletal else G.copy_mesh_from_static_mesh
 dm,status=copier(asset,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
 if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Geometry copy '+asset.get_path_name())
 _,pv,_=Q.get_all_vertex_positions(dm,False);pv=L.convert_vector_list_to_array(pv)
 _,tv,_=Q.get_all_triangle_indices(dm,False);tv=L.convert_triangle_list_to_array(tv)
 data={'source':asset.get_path_name(),'positions':[xyz(v) for v in pv],'triangles':[xyz(t) for t in tv]}
 if skeletal:
  _,bones=B.get_all_bones_info(dm);data['bone_names']=[str(b.name) for b in bones]
  data['weights']=[]
  for i in range(len(pv)):
   _,ws,valid=B.get_vertex_bone_weights(dm,i)
   data['weights'].append([[w.bone_index,w.weight] for w in ws if w.weight>0])
 return data
(OUT/'body.json').write_text(json.dumps(geometry(mesh,True),separators=(',',':')))
choices={'Chair':'/Meshes/SM_Staff_Chair.','Sofa':'/Meshes/SM_Staff_Sofa.','Bed':'/RefinementV2/Meshes/SM_AP_BedQueen.','Bunk':'/ScenePolishV4/Meshes/SM_Staff_BunkBedMessy0_V4.'}
selected={}
for kind,part in choices.items():
 row=next(p for p in profiles['furniture'] if part in p['mesh'])
 selected[kind]=row
 (OUT/(kind+'.json')).write_text(json.dumps(geometry(u.load_asset(row['mesh'])),separators=(',',':')))
(OUT/'furniture.json').write_text(json.dumps(selected,ensure_ascii=False,indent=2),encoding='utf-8')
print('REST_PREVIEW_READBACK_COMPLETE',len(rig['clips']),len(selected))
