"""Refresh explicitly referenced clips even before editor registry rescans."""
import unreal as u,pickle,hashlib,json
from pathlib import Path
r=Path(__file__).resolve().parent;d=pickle.load(open(r/'native.pkl','rb'));out=json.loads((r/'inputs.json').read_text())
mesh=u.load_asset('/Game/Weapons/M249/SK_M249_V7')
def tr(t):return [*t.translation.to_tuple(),t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w,*t.scale3d.to_tuple()]
for k in ('idle','fire','equip','inspect','quick_melee','reload','reload_empty','sprint_enter','sprint_loop','sprint_exit'):
    clip=u.load_asset('/Game/Weapons/M249/Animations/A_M249_'+k);p=clip.get_path_name();fps=120;duration=clip.get_play_length();count=round(duration*fps)+1
    d['clips'][p]=dict(fps=fps,duration=duration,frames=[[tr(v) for v in u.AnimationLibrary.get_bone_poses_for_time(clip,d['names'],min(i/fps,duration),False,mesh)] for i in range(count)])
    f=Path(u.Paths.project_content_dir())/(p.split('.')[0].removeprefix('/Game/')+'.uasset');out['hashes'][p]=hashlib.sha256(f.read_bytes()).hexdigest()
    print('M249_MOTION_SOURCE',k,count,flush=True)
with (r/'native.pkl').open('wb') as f:pickle.dump(d,f)
(r/'inputs.json').write_text(json.dumps(out,indent=2))
