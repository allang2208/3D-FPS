"""Read actual compressed animation and installed profiles after publishing."""
import unreal as u,pickle,json
from pathlib import Path
r=Path(__file__).resolve().parent;d=pickle.load(open(r/'native.pkl','rb'));mesh=u.load_asset('/Game/Weapons/M249/SK_M249_V7')
opt=u.AnimPoseEvaluationOptions();opt.evaluation_type=u.AnimDataEvalType.COMPRESSED;opt.optional_skeletal_mesh=mesh;opt.should_retarget=True
def tr(t):return [*t.translation.to_tuple(),t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w,*t.scale3d.to_tuple()]
for path,c in d['clips'].items():
    a=u.load_asset(path);duration=a.get_play_length();rows=[]
    for i in range(1 if path.split('.')[0].endswith('_idle') else round(duration*120)+1):
        pose=u.AnimPoseExtensions.get_anim_pose_at_time(a,min(i/120,duration),opt);rows.append([tr(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.LOCAL)) for n in d['names']])
    c.update(frames=rows,fps=120,duration=duration)
for family,p in d['profiles'].items():
    a=u.load_asset(p['asset']);rows=[]
    for c in a.get_editor_property('clips'):
        v=c.get_editor_property;retained=v('retained');rows.append(dict(base=v('base').get_path_name(),retained=retained.get_path_name() if retained else None,duration=v('duration'),tracks=[dict(bone=str(t.get_editor_property('bone')),times=list(t.get_editor_property('times')),values=list(t.get_editor_property('values'))) for t in v('tracks')]))
    p['clips']=rows
with (r/'saved_compressed.pkl').open('wb') as f:pickle.dump(d,f)
(r/'readback_receipt.json').write_text(json.dumps(dict(compressed=True,sample_rate=120,clips=list(d['clips']),runtime_gameplay=False),indent=2))
print('M249_REPAIR20_COMPRESSED_READBACK_SAVED',flush=True)
