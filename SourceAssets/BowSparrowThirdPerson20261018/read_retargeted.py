"""Read saved Jason candidates and skin for offline contact authoring."""
import gzip,json,gc
from pathlib import Path
import unreal as u
O=Path(__file__).parent;ROOT=O.parents[1]
cfg=json.loads((ROOT/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
mesh=u.load_asset(cfg['body_mesh']);ref=mesh.skeleton.get_reference_pose()
names=[str(n) for n in u.AnimPoseExtensions.get_bone_names(ref)]
comp=u.new_object(u.SkeletalMeshComponent);comp.set_skeletal_mesh_asset(mesh)
def pack(t):
 p,q,s=t.translation,t.rotation,t.scale3d
 return [p.x,p.y,p.z,q.x,q.y,q.z,q.w,s.x,s.y,s.z]
def write(name,value):
 with gzip.open(O/name,'wt',encoding='utf-8') as f:json.dump(value,f,separators=(',',':'))
d=dict(mesh=mesh.get_path_name(),skeleton=mesh.skeleton.get_path_name(),names=names,
 parents=[names.index(str(comp.get_parent_bone(n))) if str(comp.get_parent_bone(n)) in names else -1 for n in names],
 reference=[pack(u.AnimPoseExtensions.get_bone_pose(ref,n,u.AnimPoseSpaces.LOCAL)) for n in names],clips={},pose_scale=cfg['pose_scale'])
opt=u.AnimPoseEvaluationOptions();opt.optional_skeletal_mesh=mesh;opt.evaluation_type=u.AnimDataEvalType.SOURCE
def sample(clip):
 length=clip.get_play_length();count=max(1,round(length*30));frames=[];times=[length*i/count for i in range(count+1)]
 for t in times:
  pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,t,opt)
  frames.append([pack(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.LOCAL)) for n in names])
 return dict(asset=clip.get_path_name(),duration=length,times=times,frames=frames)
write('target-skeleton.json.gz',d)
print('SPARROW_TARGET_READ_BEGIN',len(names),flush=True)
for name in ('idle','Travel_Mode_Idle_BowDown','RMB_Drawback','RMB_Loop','RMB_Fire','Primary_Fire_Slow'):
 cache=O/('target-'+name+'.json.gz')
 if cache.exists():
  with gzip.open(cache,'rt') as f:d['clips'][name]=json.load(f)
 else:
  clip=u.load_asset('/Game/Characters/JasonPlayer20261003/BowSparrow20261018/Retargeted/J_Sparrow_'+name)
  print('SPARROW_TARGET_CLIP_BEGIN',name,flush=True)
  d['clips'][name]=sample(clip);write(cache.name,d['clips'][name]);gc.collect()
 print('SPARROW_TARGET_CLIP_SAVED',name,flush=True)
d['neutral']=sample(u.load_asset(cfg['clips']['Unarmed.Idle']));write('retargeted.json.gz',d)
Q=u.GeometryScript_MeshQueries;B=u.GeometryScript_BoneWeights
dm,status=u.GeometryScript_AssetUtils.copy_mesh_from_skeletal_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read target skin')
_,pv,_=Q.get_all_vertex_positions(dm,False);vs=u.GeometryScript_List.convert_vector_list_to_array(pv)
_,tv,_=Q.get_all_triangle_indices(dm,False);ts=u.GeometryScript_List.convert_triangle_list_to_array(tv)
_,bones=B.get_all_bones_info(dm);bn={b.index:str(b.name) for b in bones}
skin={'positions':[[v.x,v.y,v.z] for v in vs],'triangles':[[t.x,t.y,t.z] for t in ts],
      'rest':{str(b.name):pack(b.world_transform) for b in bones},'weights':[]}
for i in range(len(vs)):
 _,ws,valid=B.get_vertex_bone_weights(dm,i)
 if not valid:raise RuntimeError('Invalid target vertex weights')
 skin['weights'].append({bn[w.bone_index]:w.weight for w in ws if w.weight>0})
write('skin.json.gz',skin)
(O/'prepared.json').write_text(json.dumps({'clips':{n:c['asset'] for n,c in d['clips'].items()},'skin_vertices':len(vs),'source_url':'https://www.fab.com/listings/7d76ddf0-d9ce-4d00-939e-d72793534d01','game_run':False},indent=2))
print('SPARROW_BOW_INPUTS_SAVED',flush=True)
