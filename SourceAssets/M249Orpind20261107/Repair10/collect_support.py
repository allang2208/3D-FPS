"""Read existing support holds so the bipod return shares the same endpoint."""
from pathlib import Path
import unreal as u,pickle,json,hashlib
r=Path(__file__).resolve().parent;g=pickle.load(open(r/'geometry.pkl','rb'));names=g['names']
mesh=u.load_asset('/Game/Weapons/M249/SK_M249_V7');data={}
def tr(t):
    p=t.translation;q=t.rotation;s=t.scale3d
    return [p.x,p.y,p.z,q.x,q.y,q.z,q.w,s.x,s.y,s.z]
for path in u.EditorAssetLibrary.list_assets('/Game/Weapons/M249/Animations',False,False):
    clip=u.load_asset(path)
    if not isinstance(clip,u.AnimSequence):continue
    fps=120;duration=clip.get_play_length();count=round(duration*fps)+1
    rows=[[tr(v) for v in u.AnimationLibrary.get_bone_poses_for_time(clip,names,min(i/fps,duration),False,mesh)] for i in range(count)]
    data[path]=dict(fps=fps,duration=duration,frames=rows)
    print('SUPPORT_ANCHOR_READ',path,count,flush=True)
with (r/'support_inputs.pkl').open('wb') as f:pickle.dump(data,f)
print('SUPPORT_INPUTS_SAVED',len(data),flush=True)
