"""Adapt the CC0 Dizzy take to fixed Jason proportions and a smooth loop seam."""
import json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R

OUT=Path(__file__).resolve().parent
d=json.loads((OUT/'retargeted.json').read_text())
raw=np.array(d['frames']);idle=np.array(d['idle']);ref=np.array(d['reference'])
count=len(raw)-1
t=np.arange(count)/count
def basis(time):
    return np.column_stack([np.ones(len(time))]+[f(2*np.pi*k*time) for k in range(1,5) for f in (np.sin,np.cos)])
b=basis(t);out_b=basis(np.arange(count+1)/count)
frames=np.repeat(idle[None,:,:],count+1,axis=0)
for j,name in enumerate(d['names']):
    # Preserve the source's asymmetric balance corrections while closing value
    # and velocity at the repeat point. Fit rotations around their mean, not
    # Euler angles, to avoid wrap discontinuities and additive head stretching.
    source=R.from_quat(raw[:-1,j,3:7]);anchor=source.mean()
    tangent=(anchor.inv()*source).as_rotvec()
    coeff=np.linalg.lstsq(b,tangent,rcond=None)[0]
    fitted=anchor*R.from_rotvec(out_b@coeff)
    strength=.8 if name.startswith('spine_') else .7 if name.startswith(('neck_','head')) else 1.
    base=R.from_quat(idle[j,3:7])
    frames[:,j,3:7]=(base*R.from_rotvec((base.inv()*fitted).as_rotvec()*strength)).as_quat()
    frames[:,j,:3]=ref[j,:3];frames[:,j,7:]=ref[j,7:]
    if name in ('root','pelvis'):frames[:,j]=idle[j]
frames[-1]=frames[0]
for i in range(1,len(frames)):
    flip=np.sum(frames[i-1,:,3:7]*frames[i,:,3:7],axis=1)<0
    frames[i,flip,3:7]*=-1
result=dict(mesh=d['mesh'],skeleton=d['skeleton'],names=d['names'],rate=30,frames=frames.tolist(),
    source=d['source'],provenance='Mesh2Motion human-addon-animations Dizzy; CC0-1.0; Jason proportions and periodic rotation fitting',
    source_manifest='SourceAssets/HumanoidStun20260926/source_manifest.json')
(OUT/'authored.json').write_text(json.dumps(result,separators=(',',':')))
print('STUN_AUTHORED '+str(len(frames))+' keys')
