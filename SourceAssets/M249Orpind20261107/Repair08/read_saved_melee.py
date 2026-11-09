from pathlib import Path
import unreal as u,pickle,json
r=Path(__file__).resolve().parent
mesh=u.load_asset('/Game/Weapons/M249/SK_M249_V7');geo=pickle.load(open(r.parent/'Repair06/geometry.pkl','rb'));names=geo['names']
def tr(t):return [*t.translation.to_tuple(),t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w,*t.scale3d.to_tuple()]
for role in ('idle','quick_melee'):
    clip=u.load_asset('/Game/Weapons/M249/Animations/A_M249_'+role)
    fps=1440;count=round(clip.get_play_length()*fps)+1 if role!='idle' else 1
    rows=[[tr(v) for v in u.AnimationLibrary.get_bone_poses_for_time(clip,names,i/fps,False,mesh)] for i in range(count)]
    with (r/('SAVED_'+role+'.pkl')).open('wb') as f:pickle.dump(dict(names=names,parents=geo['parents'],frames=rows,fps=fps,duration=clip.get_play_length(),space='local'),f)
    print('M249_SAVED_MELEE_SAMPLES',role,count,flush=True)
