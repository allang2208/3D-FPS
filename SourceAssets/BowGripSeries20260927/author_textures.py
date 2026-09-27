"""Author tileable fabric/leather PBR maps, original procedural artwork."""
from pathlib import Path
import json
import numpy as np
from PIL import Image

P=Path(__file__).parent
OUT=P/'Textures'
OUT.mkdir(exist_ok=True)
N=1024
y,x=np.mgrid[0:N,0:N]
u=(x+.5)/N
v=1-(y+.5)/N
rng=np.random.default_rng(27092026)

def smooth_noise():
    a=rng.random((N,N)).astype(np.float32)
    for _ in range(5):
        a=(a+np.roll(a,1,0)+np.roll(a,-1,0)+np.roll(a,1,1)+np.roll(a,-1,1))/5
    return (a-a.mean())/max(float(a.std()),1e-6)

records=[]
for row in json.loads((P/'series.json').read_text(encoding='utf8'))['variants']:
    grain=smooth_noise()
    pores=rng.random((N,N)).astype(np.float32)
    if row['name']=='WovenLinen':
        warp=np.cos(2*np.pi*(u*64+v*52))
        weft=np.cos(2*np.pi*(u*64-v*52))
        weave=np.maximum(warp,weft)
        twist=np.sin(2*np.pi*(u*384+v*312))
        h=.52*weave+.055*twist+.03*grain
        shade=.94+.12*weave+.025*grain
        rough=row['roughness']+.025*grain
    else:
        # Sparse pores and broad leather grain; both wrap seamlessly in U.
        broad=np.sin(2*np.pi*(13*u+7*v))*.4+np.sin(2*np.pi*(37*u-19*v))*.3
        h=.07*grain+.045*broad-.11*(pores>.96)
        shade=.97+.045*grain+.025*broad
        rough=row['roughness']+.045*grain
        if row['name']=='SlimLeather':
            phase=(v*8-u)%1
            edge=np.exp(-((np.minimum(phase,1-phase))/.045)**2)
            shade-=edge*.16
            h-=edge*.16
        else:
            # Soft channel beneath the real stitching at the front-side seam.
            d=np.abs(u-.25)
            seam=np.exp(-(d/.010)**2)
            shade-=.14*seam
            h-=.20*seam
    rgb=np.clip(np.array(row['color'])[None,None,:]*shade[:,:,None],0,1)
    ao=np.clip(.94+.035*h, .80,1)
    orm=np.stack((ao,np.clip(rough,.38,.93),np.zeros_like(ao)),axis=-1)
    dy=(np.roll(h,-1,0)-np.roll(h,1,0))*.5
    dx=(np.roll(h,-1,1)-np.roll(h,1,1))*.5
    normal=np.stack((-dx*1.7,dy*1.7,np.ones_like(dx)),axis=-1)
    normal/=np.linalg.norm(normal,axis=-1,keepdims=True)
    for kind,arr in [('BaseColor',rgb),('ORM',orm),('Normal',normal*.5+.5)]:
        filename='T_Bow_Grip_'+row['name']+'_'+kind+'.png'
        Image.fromarray(np.uint8(np.clip(arr,0,1)*255)).save(OUT/filename)
        records.append({'file':filename,'kind':kind,'size':[N,N]})
(P/'texture-authoring.json').write_text(json.dumps({'maps':records,'source':'original procedural weave and leather','normal_convention':'OpenGL +Y; UE importer flips green'},indent=2),encoding='utf8')
print('BOW_GRIP_PBR_AUTHORED',len(records))
