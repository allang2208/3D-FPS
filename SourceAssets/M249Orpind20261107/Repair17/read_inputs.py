"""Read current native contacts and the accepted M4 magazine grasp for authoring."""
import unreal as u,json,pickle,hashlib
from pathlib import Path
r=Path(__file__).resolve().parent
d=pickle.load(open(r.parent/'Repair13/native.pkl','rb'))
receipt={'hashes':{},'runtime_tested':False}
def record(a):
    path=a.get_path_name();f=Path(u.Paths.project_content_dir())/(path.split('.')[0].removeprefix('/Game/')+'.uasset')
    receipt['hashes'][path]=hashlib.sha256(f.read_bytes()).hexdigest()
def tr(t):return [*t.translation.to_tuple(),t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w,*t.scale3d.to_tuple()]
mesh=u.load_asset('/Game/Weapons/M249/SK_M249_V7');record(mesh)
for role in ('idle','reload_empty'):
    a=u.load_asset('/Game/Weapons/M249/Animations/A_M249_'+role);record(a);fps=60;duration=a.get_play_length()
    d['clips'][a.get_path_name()]={'fps':fps,'duration':duration,'frames':[[tr(t) for t in u.AnimationLibrary.get_bone_poses_for_time(a,d['names'],min(i/fps,duration),False,mesh)] for i in range(round(duration*fps)+1)]}
d['profiles']={}
for family in ('base','vertical','canted','prism','angled'):
    path='/Game/Weapons/M249/Bipod/DA_M249_SupportGrip' if family=='base' else '/Game/Weapons/M249/CommonParts20261108/Profiles/DA_M249_'+family
    a=u.load_asset(path);record(a)
    d['profiles'][family]={'asset':path,'clips':[dict(base=c.get_editor_property('base').get_path_name(),retained=c.get_editor_property('retained').get_path_name() if c.get_editor_property('retained') else None,duration=c.get_editor_property('duration'),tracks=[dict(bone=str(t.get_editor_property('bone')),times=list(t.get_editor_property('times')),values=list(t.get_editor_property('values'))) for t in c.get_editor_property('tracks')]) for c in a.get_editor_property('clips')]}
donor=u.load_asset('/Game/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416')
dm,result=u.GeometryScript_AssetUtils.copy_mesh_from_skeletal_mesh(donor,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
_,bones=u.GeometryScript_BoneWeights.get_all_bones_info(dm);bones=sorted(bones,key=lambda b:b.index)
names=[str(b.name) for b in bones];clip=u.load_asset('/Game/Weapons/ExtMagContact20260919/A_M4_ExtContact_reload');record(clip)
grasp={'names':names,'parents':[b.parent_index for b in bones],'bind':[tr(b.world_transform) for b in bones],'path':clip.get_path_name(),'time':1.24,'local':[tr(t) for t in u.AnimationLibrary.get_bone_poses_for_time(clip,names,1.24,False,donor)]}
with (r/'native.pkl').open('wb') as f:pickle.dump(d,f)
with (r/'grasp.pkl').open('wb') as f:pickle.dump(grasp,f)
(r/'inputs.json').write_text(json.dumps(receipt,indent=2))
print('M249_SIDE_MAG_INPUTS_SAVED',flush=True)
