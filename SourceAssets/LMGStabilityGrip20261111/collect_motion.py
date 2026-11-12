"""Read the two hosts' current authored vertical-grip inputs; no game execution."""
import unreal as u,json,gzip
from pathlib import Path
HERE=Path(__file__).resolve().parent;data=json.loads((HERE/'inputs.json').read_text())
def tr(t):return [*t.translation.to_tuple(),t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w,*t.scale3d.to_tuple()]
for key in ['LMG201','PKM']:
    d=data[key];mesh=u.load_asset(d['mesh']);clips={}
    for row in d['profiles']['vertical']['clips']:
        a=u.load_asset(row['base']);duration=a.get_play_length();times=[min(i/60,duration) for i in range(round(duration*60)+1)]
        clips[row['base']]=dict(times=times,duration=duration,frames=[[tr(t) for t in u.AnimationLibrary.get_bone_poses_for_time(a,d['names'],t,False,mesh)] for t in times])
    with gzip.open(HERE/(key+'_motion.json.gz'),'wt') as f:json.dump(clips,f,separators=(',',':'))
    print('Authored motion inputs saved',key,len(clips),flush=True)
