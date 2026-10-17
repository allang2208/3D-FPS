"""Read the currently loaded M870 reload and native skin for the requested diagnosis."""
import unreal as u,json,gzip,hashlib
from pathlib import Path
O=Path(__file__).parent;P=O.parents[1]
ROOT='/Game/Weapons/M870/Tactical20261015'
Q=u.GeometryScript_MeshQueries;G=u.GeometryScript_AssetUtils;B=u.GeometryScript_BoneWeights
def xyz(v):return [v.x,v.y,v.z]
def tr(t):return [*xyz(t.translation),t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w,*xyz(t.scale3d)]
def sha(path):return hashlib.sha256((P/'Content'/(path.removeprefix('/Game/')+'.uasset')).read_bytes()).hexdigest()
path='/Game/Characters/ModularOutfit20260924/Super90Source20261006/Super90/SK_Super90_BareArmsV7'
mesh=u.load_asset(path)
dm,status=G.copy_mesh_from_skeletal_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Native skin extraction failed')
_,pv,_=Q.get_all_vertex_positions(dm,False);ps=u.GeometryScript_List.convert_vector_list_to_array(pv)
_,tv,_=Q.get_all_triangle_indices(dm,False);ts=u.GeometryScript_List.convert_triangle_list_to_array(tv)
_,bones=B.get_all_bones_info(dm);names={b.index:str(b.name) for b in bones}
d={'path':path,'sha256':sha(path),'vertices':[xyz(p) for p in ps],'faces':[xyz(t) for t in ts],
 'rest':{str(b.name):tr(b.world_transform) for b in bones},'parents':{str(b.name):names.get(b.parent_index) for b in bones},'weights':[]}
for vi in range(len(ps)):
 _,ws,ok=B.get_vertex_bone_weights(dm,vi)
 if not ok:raise RuntimeError('Native weights '+str(vi))
 d['weights'].append({names[w.bone_index]:w.weight for w in ws if w.weight>0})
with gzip.open(O/'native_arms.json.gz','wt',encoding='utf-8') as f:json.dump(d,f,separators=(',',':'))
report={'native_skin':{'path':path,'sha256':d['sha256'],'vertices':len(ps)},'clips':{}}
sample_frames=[0,9,18,24,30,40,44,48,54,60,74,84,94,104,144,194,244,294,344,350,359,360,366,372,390,399,410,424]
for role in ('reload_continuous','reload_full'):
 path=ROOT+'/Animations/A_M870_'+role;clip=u.load_asset(path)
 entry={'path':path,'sha256':sha(path),'length':clip.get_play_length(),'samples':{}}
 for mode in ('RAW','COMPRESSED'):
  options=u.AnimPoseEvaluationOptions();options.evaluation_type=getattr(u.AnimDataEvalType,mode);options.should_retarget=False
  samples=[]
  for frame in sample_frames:
   t=frame/60
   if t>entry['length']+.0001:continue
   pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,t,options)
   ns=u.AnimPoseExtensions.get_bone_names(pose)
   selected=[str(n) for n in ns if str(n).endswith('_r') or str(n) in ('WPN_Shell','WPN_root')]
   samples.append({'frame':frame,'world':{n:tr(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.WORLD)) for n in selected}})
  entry['samples'][mode]=samples
 report['clips'][role]=entry
 print('M870_RELOAD_READ',role,flush=True)
(O/'installed.json').write_text(json.dumps(report,separators=(',',':')),encoding='utf-8')
print('M870_CURRENT_RELOAD_INPUTS_SAVED',flush=True)
