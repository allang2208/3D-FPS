"""Read saved compressed poses and actual profile layers after the scoped repair."""
from pathlib import Path
import unreal as u,pickle,json,hashlib
r=Path(__file__).resolve().parent;d=pickle.load(open(r/'native.pkl','rb'));mesh=u.load_asset('/Game/Weapons/M249/SK_M249_V7')
opt=u.AnimPoseEvaluationOptions();opt.evaluation_type=u.AnimDataEvalType.COMPRESSED;opt.optional_skeletal_mesh=mesh;opt.should_retarget=True
def tr(t):return [*t.translation.to_tuple(),t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w,*t.scale3d.to_tuple()]
for path in [k for k in d['clips'] if '/SideMagazine20261108/Animations/' in k or k.split('.')[0].endswith('_idle')]:
    a=u.load_asset(path);fps=120;duration=a.get_play_length();frames=[]
    for i in range(1 if path.split('.')[0].endswith('_idle') else round(duration*fps)+1):
        pose=u.AnimPoseExtensions.get_anim_pose_at_time(a,min(i/fps,duration),opt)
        frames.append([tr(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.LOCAL)) for n in d['names']])
    d['clips'][path]=dict(fps=fps,duration=duration,frames=frames)
for family,p in d['profiles'].items():
    a=u.load_asset(p['asset']);rows=[]
    for c in a.get_editor_property('clips'):
        retained=c.get_editor_property('retained')
        rows.append(dict(base=c.get_editor_property('base').get_path_name(),retained=retained.get_path_name() if retained else None,duration=c.get_editor_property('duration'),tracks=[dict(bone=str(t.get_editor_property('bone')),times=list(t.get_editor_property('times')),values=list(t.get_editor_property('values'))) for t in c.get_editor_property('tracks')]))
    p['clips']=rows
with (r/'saved_compressed.pkl').open('wb') as f:pickle.dump(d,f)
(r/'readback_receipt.json').write_text(json.dumps(dict(compressed=True,sample_rate=120,grip_families=list(d['profiles']),runtime_gameplay=False),indent=2))
print('M249_COMPRESSED_LEFT_RELOAD_READBACK_SAVED')
