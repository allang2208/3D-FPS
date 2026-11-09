"""Read authoritative local tracks by data-model time, preserving the native hierarchy."""
from pathlib import Path
import unreal as u,pickle
r=Path(__file__).resolve().parent;mesh=u.load_asset('/Game/Weapons/M249/SK_M249_V7')
geometry=pickle.load(open(r.parent/'Repair06/geometry.pkl','rb'));names=geometry['names']
def tr(t):return [*t.translation.to_tuple(),t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w,*t.scale3d.to_tuple()]
for role in ('idle','quick_melee'):
    clip=u.load_asset('/Game/Weapons/M249/Animations/A_M249_'+role);model=clip.get_editor_property('data_model_interface');rate=model.get_frame_rate()
    fps=rate.numerator/rate.denominator;count=model.get_number_of_keys() if role!='idle' else 1
    frames=[[tr(v) for v in u.AnimationLibrary.get_bone_poses_for_time(clip,names,i/fps,False,mesh)] for i in range(count)]
    with (r/('DATA_MODEL_'+role+'.pkl')).open('wb') as f:pickle.dump(dict(names=names,parents=geometry['parents'],frames=frames,fps=fps,duration=clip.get_play_length(),space='local'),f)
    print('M249_DATA_MODEL',role,count,fps,flush=True)
