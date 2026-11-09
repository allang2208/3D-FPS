"""Collect saved M24 action plus its live grip differences, and M249 native idle."""
from pathlib import Path
import unreal as u,json,pickle
r=Path(__file__).resolve().parent;sa=r.parents[1]
def tr(t):return [*t.translation.to_tuple(),t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w,*t.scale3d.to_tuple()]
def clip(path,names,mesh,first=False):
    a=u.load_asset(path);dm=a.get_editor_property('data_model_interface');rate=dm.get_frame_rate();fps=rate.numerator/rate.denominator
    return dict(path=a.get_path_name(),fps=fps,duration=a.get_play_length(),frames=[[tr(v) for v in u.AnimationLibrary.get_bone_poses_for_time(a,names,i/fps,False,mesh)] for i in range(1 if first else dm.get_number_of_keys())])
rig=json.loads((sa/'M24ArmRebuild20261027/source_after.json').read_text());names=list(rig['rest'])
mesh=u.load_asset('/Game/Weapons/M24/MotionMagazine20261027/SK_M24_MotionV9')
profile=u.load_asset('/Game/Weapons/M24/MotionPolish20261027/DA_M24_SupportGrip')
clips=[]
for c in profile.get_editor_property('clips'):
    path=c.get_editor_property('base').get_path_name()
    if '/A_M24_Bipod_base' in path or '/A_M24_idle.' in path:
        clips.append(dict(base=path,duration=c.get_editor_property('duration'),tracks=[dict(bone=str(t.get_editor_property('bone')),times=list(t.get_editor_property('times')),values=list(t.get_editor_property('values'))) for t in c.get_editor_property('tracks')]))
d=dict(names=names,parents=rig['parents'],bind=rig['rest'],profile=clips)
d['idle']=clip('/Game/Weapons/M24/Hold20261027/Animations/A_M24_idle',names,mesh,True)
d['bipod']=clip('/Game/Weapons/M24/ContactRepair20261101/A_M24_Bipod_base',names,mesh)
with (r/'m24_inputs.pkl').open('wb') as f:pickle.dump(d,f)
geo=pickle.load(open(r.parent/'Repair06/geometry.pkl','rb'));mesh=u.load_asset('/Game/Weapons/M249/SK_M249_V7')
d=clip('/Game/Weapons/M249/Animations/A_M249_idle',geo['names'],mesh,True);d.update(names=geo['names'],parents=geo['parents'],bind=geo['bind'])
with (r/'m249_inputs.pkl').open('wb') as f:pickle.dump(d,f)
print('M249_BIPOD_AUTHOR_INPUTS_SAVED',len(clips),flush=True)
