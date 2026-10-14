"""Adapt Kevin Death01 to Jason, with a complete fall/settle and camera tracks.

Keeps the full-body donor rotations; no FPS hand animation is substituted.
Outputs are local authoring material under the source asset's existing license.
"""
import json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R
from scipy.ndimage import gaussian_filter1d

OUT=Path(__file__).resolve().parent
d=json.loads((OUT/'kevin-authoring-input.json').read_text())
names,parents=d['names'],d['parents']
ix={n:i for i,n in enumerate(names)}
ref=np.array(d['reference'])
source=np.array(d['frames'])

def fk(f):
    w=f.copy()
    for i,p in enumerate(parents):
        if p<0:continue
        q=R.from_quat(w[p,3:7])
        w[i,:3]=w[p,:3]+q.apply(f[i,:3]*w[p,7:])
        w[i,3:7]=(q*R.from_quat(f[i,3:7])).as_quat()
        w[i,7:]=w[p,7:]*f[i,7:]
    return w

def pose(t):
    x=np.clip(t/d['duration'],0,1)*(len(source)-1)
    a=min(int(x),len(source)-2)
    u=x-a
    f=source[a]*(1-u)+source[a+1]*u
    q=source[a+1,:,3:7].copy()
    q[np.sum(q*source[a,:,3:7],axis=1)<0]*=-1
    f[:,3:7]=source[a,:,3:7]*(1-u)+q*u
    f[:,3:7]/=np.linalg.norm(f[:,3:7],axis=1)[:,None]
    w=fk(f)
    # Bake source root displacement into the pelvis, retaining a fixed actor
    # root. Keep all non-pelvis offsets at Jason's native bone lengths.
    f[:,:3]=ref[:,:3]
    f[:,7:]=ref[:,7:]
    f[ix['root']]=ref[ix['root']]
    f[ix['pelvis'],:7]=w[ix['pelvis'],:7]
    # Small floor support allowance for retargeted palms, shoes and head.
    w=fk(f)
    supports={'ball_l':1.,'ball_r':1.,'hand_l':2.,'hand_r':2.,'head':9.,'pelvis':9.}
    lift=max([0.]+[height-w[ix[b],2] for b,height in supports.items()])
    f[ix['pelvis'],2]+=lift
    return f

clips={}
for label,duration,times,sources in [
    ('Standing',1.4,[0.,.34,.65,1.,1.4],[0.,.133333,.266667,.466667,d['duration']]),
    ('Crouched',1.2,[0.,.26,.73,1.2],[.133333,.266667,.466667,d['duration']]),
]:
    count=round(duration*30)+1
    frames=np.array([pose(float(np.interp(t,times,sources))) for t in np.linspace(0,duration,count)])
    heads=[fk(f)[ix['head']] for f in frames]
    initial=R.from_quat(heads[0][3:7])
    camera=[]
    for i,h in enumerate(heads):
        age=i/30
        turn=R.from_quat(h[3:7])*initial.inv()
        forward=turn.apply([0,1,0])
        pitch=np.clip(np.degrees(np.arcsin(np.clip(forward[2],-1,1))),-58,30)
        yaw=np.clip(np.degrees(np.arctan2(-forward[0],forward[1])),-12,12)
        # A restrained cheek roll and a readable low horizon during settling.
        settle=np.clip((age-times[-2])/(duration-times[-2]),0,1)
        settle=settle*settle*(3-2*settle)
        pitch=pitch*(1-settle)-14*settle
        roll=18*(i/(count-1))**2
        camera.append([*(h[:3]+[0,7,5]),pitch,yaw,roll])
    camera=np.array(camera)
    camera[:,3:]=gaussian_filter1d(camera[:,3:],.7,axis=0,mode='nearest')
    for i in range(1,count):
        flip=np.sum(frames[i-1,:,3:7]*frames[i,:,3:7],axis=1)<0
        frames[i,flip,3:7]*=-1
    clips[label]=dict(rate=30,frames=frames.tolist(),camera=np.round(camera,5).tolist(),impact=times[-2])
result=dict(mesh=d['mesh'],skeleton=d['skeleton'],names=names,clips=clips,source=d['source'],
    source_url='https://kevdev.itch.io/human-melee-animatons-free',
    provenance='Kevin Iglesias Human Melee Animations FREE Death01; Jason retarget, native bone lengths, authored timing and floor support')
(OUT/'authored-death.json').write_text(json.dumps(result,separators=(',',':')),encoding='utf-8')
print('PLAYER_DEATH_AUTHORED Standing=43 keys / Crouched=37 keys, with camera tracks')
