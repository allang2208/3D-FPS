"""Read current side-magazine reloads and their live grip profiles for editing."""
from pathlib import Path
import unreal as u,pickle,json,hashlib
r=Path(__file__).resolve().parent;project=r.parents[2]
d=pickle.load(open(r.parent/'Repair20/native.pkl','rb'));d['clips']={};hashes={}
def record(a):
    path=a.get_path_name().split('.')[0]
    hashes[path]=hashlib.sha256((project/'Content'/(path.removeprefix('/Game/')+'.uasset')).read_bytes()).hexdigest()
def tr(t):return [*t.translation.to_tuple(),t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w,*t.scale3d.to_tuple()]
mesh=u.load_asset('/Game/Weapons/M249/SK_M249_V7');record(mesh)
opt=u.AnimPoseEvaluationOptions();opt.evaluation_type=u.AnimDataEvalType.COMPRESSED;opt.optional_skeletal_mesh=mesh;opt.should_retarget=True
paths=['/Game/Weapons/M249/Animations/A_M249_idle']+['/Game/Weapons/M249/SideMagazine20261108/Animations/A_M249_side_'+role for role in ['reload','reload_empty']]
for path in paths:
    clip=u.load_asset(path);record(clip);duration=clip.get_play_length();times=[0.] if path.endswith('_idle') else [i/120 for i in range(round(duration*120)+1)];rows=[]
    for t in times:
        pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,t,opt)
        rows.append([tr(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.LOCAL)) for n in d['names']])
    d['clips'][clip.get_path_name()]=dict(fps=120,duration=duration,frames=rows)
for family,p in d['profiles'].items():
    a=u.load_asset(p['asset']);record(a);rows=[]
    for c in a.get_editor_property('clips'):
        v=c.get_editor_property;retained=v('retained')
        rows.append(dict(base=v('base').get_path_name(),retained=retained.get_path_name() if retained else None,duration=v('duration'),tracks=[dict(bone=str(t.get_editor_property('bone')),times=list(t.get_editor_property('times')),values=list(t.get_editor_property('values'))) for t in v('tracks')]))
    p['clips']=rows
with (r/'current.pkl').open('wb') as f:pickle.dump(d,f)
(r/'inputs.json').write_text(json.dumps(dict(hashes=hashes,clips=paths),indent=2))
print('M249_RETURN23_INPUTS_READ',len(d['clips']),len(d['profiles']),flush=True)
