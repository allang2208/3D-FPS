import unreal as u,pickle,json
from pathlib import Path
r=Path(__file__).resolve().parent;d=pickle.load(open(r.parent/'Repair20/saved_compressed.pkl','rb'));mesh=u.load_asset('/Game/Weapons/M249/SK_M249_V7');path='/Game/Weapons/M249/Animations/A_M249_idle';clip=u.load_asset(path)
opt=u.AnimPoseEvaluationOptions();opt.evaluation_type=u.AnimDataEvalType.COMPRESSED;opt.optional_skeletal_mesh=mesh;opt.should_retarget=True
rows=[]
for k in range(121):
 pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,k/120.,opt);row=[]
 for name in d['names']:
  t=u.AnimPoseExtensions.get_bone_pose(pose,name,u.AnimPoseSpaces.LOCAL);row.append([*t.translation.to_tuple(),t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w,*t.scale3d.to_tuple()])
 rows.append(row)
for family,p in d['profiles'].items():
 a=u.load_asset(p['asset']);clips=[]
 for c in a.get_editor_property('clips'):
  v=c.get_editor_property;clips.append(dict(base=v('base').get_path_name(),duration=v('duration'),retained=v('retained').get_path_name() if v('retained') else None,tracks=[dict(bone=str(t.get_editor_property('bone')),times=list(t.get_editor_property('times')),values=list(t.get_editor_property('values'))) for t in v('tracks')]))
 p['clips']=clips
key=next(p for p in d['clips'] if '_idle.' in p);d['clips']={key:dict(duration=clip.get_play_length(),fps=120,frames=rows)}
with open(r/'idle_raw.pkl','wb') as f:pickle.dump(d,f)
print('M249_CURRENT_IDLE_READ',len(rows),flush=True)
