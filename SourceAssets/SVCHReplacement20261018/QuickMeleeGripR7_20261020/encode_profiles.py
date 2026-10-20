"""Retain R6's compressed-subframe correction while encoding the new grasp."""
from diagnose_grip import O,R6,s
import json,gzip,copy,numpy as np,sys
sys.path.insert(0,str(R6));from author_subframes import lerp_transform
raw=json.load(gzip.open(R6/'compressed-1920.json.gz','rt'));fine=json.load(gzip.open(R6/'compressed-window-15360.json.gz','rt'))
order=[raw['names'].index(n) for n in s.names];base=np.array(raw['frames'])[:,order];finebase=np.array(fine['frames'])[:,order]
desired=np.load(O/'desired-local-120.npz')
# Entry/recovery's existing visible pose is baked for every channel. This is
# required when the native action blend is disabled; non-right motion is the
# unchanged R6 runtime result, not a new gun/left-arm path.
right=list(range(len(s.names)))
times=np.unique(np.r_[np.arange(109)/120,np.arange(54*8,90*8+1)/960,np.arange(66*64,70*64+1)/7680])
from scipy.spatial.transform import Rotation as R
for family in desired.files:
    original=json.loads((R6/'SavedReadback'/f'{family}.json').read_text());result=copy.deepcopy(original)
    layer=next(c for c in result['clips'] if c['base']==raw['path']);tracks={j:[] for j in right};local=desired[family]
    for t in times:
        frame=t*120;i=min(int(np.floor(frame+1e-7)),107);w=np.clip(frame-i,0,1);target=lerp_transform(local[i],local[i+1],w)
        b=finebase[round(t*15360)-66*128] if 66/120-1e-9<=t<=70/120+1e-9 else base[round(t*1920)]
        for j in right:
            v=np.r_[target[j,:3]-b[j,:3],(R.from_quat(target[j,3:7])*R.from_quat(b[j,3:7]).inv()).as_quat(),target[j,7:]-b[j,7:]]
            if tracks[j] and tracks[j][-1][3:7]@v[3:7]<0:v[3:7]*=-1
            tracks[j].append(v)
    layer['tracks']=[t for t in layer['tracks'] if s.ids[t['bone']] not in right]+[
        {'bone':s.names[j],'times':times.tolist(),'values':np.array(v).ravel().tolist()} for j,v in tracks.items()]
    (O/'Profiles').mkdir(exist_ok=True);(O/'Profiles'/f'{family}.json').write_text(json.dumps(result,separators=(',',':')))
print('R7_FIVE_PROFILES_ENCODED',len(times),flush=True)
