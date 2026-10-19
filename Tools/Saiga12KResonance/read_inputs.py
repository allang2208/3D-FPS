"""Read only S12K's current resonance grip, sparse profile and source poses."""
import unreal as u
import json,gzip,hashlib
from pathlib import Path

P=Path('D:/FPS3D/FPSGAME');O=P/'SourceAssets/Saiga12KResonance20261019'
(O/'Inputs').mkdir(parents=True,exist_ok=True)
E=u.EditorAssetLibrary;AP=u.AnimPoseExtensions
grip_path='/Game/Weapons/Saiga12K/Detail20261018/Attachments/SM_Saiga12K_angled'
profile_path='/Game/Weapons/Saiga12K/InspectClearance20261018/Profiles/DA_angled'
mesh=u.load_asset('/Game/Weapons/Saiga12K/Detail20261018/SK_Saiga12K_Manny')
grip=u.load_asset(grip_path);profile=u.load_asset(profile_path)
def pack(t):
 return [getattr(t.translation,c) for c in 'xyz']+[getattr(t.rotation,c) for c in 'xyzw']+[getattr(t.scale3d,c) for c in 'xyz']
def dump_profile(p):
 clips=[]
 for c in p.get_editor_property('clips'):
  base=c.get_editor_property('base');retained=c.get_editor_property('retained')
  clips.append({'base':base.get_path_name(),'duration':c.get_editor_property('duration'),'retained':retained.get_path_name() if retained else None,'tracks':[{'bone':str(t.get_editor_property('bone')),'times':list(t.get_editor_property('times')),'values':list(t.get_editor_property('values'))} for t in c.get_editor_property('tracks')]})
 return {'family':str(p.get_editor_property('family')),'clips':clips}
spec=dump_profile(profile)
(O/'Inputs/profile.json').write_text(json.dumps(spec),encoding='utf8')
G=u.GeometryScript_AssetUtils;Q=u.GeometryScript_MeshQueries;L=u.GeometryScript_List;MT=u.GeometryScript_Materials
dm,status=G.copy_mesh_from_static_mesh(grip,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(apply_build_settings=False,request_tangents=True),u.GeometryScriptMeshReadLOD(lod_type=u.GeometryScriptLODType.SOURCE_MODEL))
if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read installed resonance grip')
_,points,_=Q.get_all_vertex_positions(dm,False);points=list(L.convert_vector_list_to_array(points))
_,triangles,_=Q.get_all_triangle_indices(dm,False);triangles=list(L.convert_triangle_list_to_array(triangles))
geo={'path':grip_path,'positions':[[v.x,v.y,v.z] for v in points],'triangles':[[t.x,t.y,t.z] for t in triangles],'materials':[MT.get_triangle_material_id(dm,i)[0] for i in range(len(triangles))],'slots':[{'name':str(s.material_slot_name),'material':s.material_interface.get_path_name() if s.material_interface else None} for s in grip.static_materials]}
(O/'Inputs/grip.json').write_text(json.dumps(geo),encoding='utf8')
opts=u.AnimPoseEvaluationOptions();opts.optional_skeletal_mesh=mesh;opts.evaluation_type=u.AnimDataEvalType.RAW;opts.incorporate_root_motion_into_pose=False
data={'clips':{}}
for c in spec['clips']:
 clip=u.load_asset(c['retained'] or c['base']);duration=clip.get_play_length();frames=[]
 steps=max(1,round(duration*120))
 for i in range(steps+1):
  time=duration*i/steps;pose=AP.get_anim_pose_at_time(clip,time,opts)
  names=[str(n) for n in AP.get_bone_names(pose)]
  frames.append({'time':time,'local':{n:pack(AP.get_bone_pose(pose,n,u.AnimPoseSpaces.LOCAL)) for n in names}})
 data['clips'][c['base']]={'asset':clip.get_path_name(),'duration':duration,'frames':frames}
 print('S12K_RESONANCE_READ',clip.get_name(),len(frames),flush=True)
with gzip.open(O/'Inputs/poses.json.gz','wt',encoding='utf8') as f:json.dump(data,f)
receipt={'complete':True,'grip':grip_path,'profile':profile_path,'clips':len(spec['clips']),'dirty':[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()],'pie':u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor()}
(O/'Inputs/read-receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf8')
print(json.dumps(receipt))
