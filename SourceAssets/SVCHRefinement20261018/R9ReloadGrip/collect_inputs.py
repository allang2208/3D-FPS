"""Read current assets for native-V9 magazine contact authoring; never save assets."""
import json,gzip,hashlib
from pathlib import Path
import unreal as u

O=Path(__file__).parent;I=O/'Inputs';I.mkdir(exist_ok=True);P=Path(u.Paths.project_dir()).resolve()
ASSETS={
 'svch':'/Game/Weapons/SVCH/Refined20261018/R8Surface/SK_SVCH_R8Surface',
 'svd':'/Game/Weapons/SVDDragunov20260922/StockAdapter20260923/SK_SVD_ModularStock',
 'arms':'/Game/Characters/ModularOutfit20260924/BarePalmV7/SVD/SK_SVD_BareArmsV7'}
manifest={}
def xf(t):
 p,q,s=t.translation,t.rotation,t.scale3d
 return [p.x,p.y,p.z,q.x,q.y,q.z,q.w,s.x,s.y,s.z]
def digest(path):
 return hashlib.sha256((P/'Content'/(path.removeprefix('/Game/')+'.uasset')).read_bytes()).hexdigest()
def pick(result,cls):return next(v for v in result if isinstance(v,cls))
G,Q,B,L=u.GeometryScript_AssetUtils,u.GeometryScript_MeshQueries,u.GeometryScript_BoneWeights,u.GeometryScript_List
for key,path in ASSETS.items():
 mesh=u.load_asset(path)
 if not mesh:raise RuntimeError('Missing '+path)
 mod=u.SkeletonModifier();mod.set_skeletal_mesh(mesh);names=list(mod.get_all_bone_names())
 data={'path':path,'sha256':digest(path),'names':[str(n) for n in names],
       'parents':[str(mod.get_parent_name(n)) for n in names],
       'reference':[xf(mod.get_bone_transform(n,True)) for n in names],
       'materials':[str(s.material_slot_name) for s in mesh.get_editor_property('materials')]}
 del mod
 dm=u.DynamicMesh();lod=u.GeometryScriptMeshReadLOD();lod.lod_type=u.GeometryScriptLODType.SOURCE_MODEL
 result=G.copy_mesh_from_skeletal_mesh(mesh,dm,u.GeometryScriptCopyMeshFromAssetOptions(),lod)
 if u.GeometryScriptOutcomePins.SUCCESS not in result:raise RuntimeError('Cannot read '+path)
 positions=L.convert_vector_list_to_array(pick(Q.get_all_vertex_positions(dm,False),u.GeometryScriptVectorList))
 triangles=L.convert_triangle_list_to_array(pick(Q.get_all_triangle_indices(dm,False),u.GeometryScriptTriangleList))
 slots=L.convert_index_list_to_array(pick(u.GeometryScript_Materials.get_all_triangle_material_i_ds(dm),u.GeometryScriptIndexList))
 data.update(positions=[[v.x,v.y,v.z] for v in positions],triangles=[[t.x,t.y,t.z] for t in triangles],material_ids=list(slots))
 _,bones=B.get_all_bones_info(dm);data['weight_bones']=[str(b.name) for b in sorted(bones,key=lambda b:b.index)]
 data['weights']=[]
 for v in range(len(positions)):
  _,ws,valid=B.get_vertex_bone_weights(dm,v)
  data['weights'].append([[w.bone_index,w.weight] for w in ws if w.weight>0])
 with gzip.open(I/(key+'.json.gz'),'wt',encoding='utf-8') as f:json.dump(data,f,separators=(',',':'))
 manifest[key]={'path':path,'sha256':data['sha256'],'vertices':len(positions),'triangles':len(triangles),'materials':data['materials']}
 print('SVCH_RELOAD_INPUT',key,len(positions),len(triangles),data['materials'],flush=True)

profile_path='/Game/Weapons/SVCH/Refined20261018/R5/DA_SVCH_BaseGrip'
profile=u.load_asset(profile_path);before={'family':str(profile.get_editor_property('family')),'clips':[]}
for clip in profile.get_editor_property('clips'):
 row={'base':clip.get_editor_property('base').get_path_name().split('.')[0],'duration':clip.get_editor_property('duration'),'tracks':[]}
 if clip.get_editor_property('retained'):raise RuntimeError('Unexpected retained clip; preserve current profile')
 for track in clip.get_editor_property('tracks'):
  row['tracks'].append({'bone':str(track.get_editor_property('bone')),'times':list(track.get_editor_property('times')),'values':list(track.get_editor_property('values'))})
 before['clips'].append(row)
(I/'profile_before.json').write_text(json.dumps(before,separators=(',',':')))
manifest['profile']={'path':profile_path,'sha256':digest(profile_path)}

mesh=u.load_asset(ASSETS['svd']);mod=u.SkeletonModifier();mod.set_skeletal_mesh(mesh);names=list(mod.get_all_bone_names())
motion={'names':[str(n) for n in names],'parents':[str(mod.get_parent_name(n)) for n in names],'clips':{}}
del mod
opts=u.AnimPoseEvaluationOptions();opts.optional_skeletal_mesh=mesh;opts.evaluation_type=u.AnimDataEvalType.COMPRESSED
for kind in ('idle','reload','reload_empty'):
 path='/Game/Weapons/SVDDragunov20260922/Complete20260923/Animations/A_SVD_'+kind
 seq=u.load_asset(path);duration=seq.get_play_length();frames=[]
 times=[0.] if kind=='idle' else [min(i/120,duration) for i in range(round(duration*120)+1)]
 for t in times:
  pose=u.AnimPoseExtensions.get_anim_pose_at_time(seq,t,opts)
  frames.append([xf(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.LOCAL)) for n in names])
 motion['clips'][kind]={'path':path,'duration':duration,'fps':120,'times':times,'frames':frames,'sha256':digest(path)}
 print('SVCH_RELOAD_CLIP',kind,len(frames),flush=True)
with gzip.open(I/'motion.json.gz','wt',encoding='utf-8') as f:json.dump(motion,f,separators=(',',':'))
(I/'manifest.json').write_text(json.dumps(manifest,indent=2))
print('SVCH_RELOAD_INPUTS_SAVED',flush=True)
