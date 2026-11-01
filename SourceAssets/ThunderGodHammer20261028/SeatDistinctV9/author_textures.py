"""Dedicated UV-space forged-metal engraving for the three-dimensional crown."""
from pathlib import Path
import numpy as np
from PIL import Image
P=Path(__file__).resolve().parent/'Textures';P.mkdir(parents=True,exist_ok=True)
size=2048;v,u=np.mgrid[0:size,0:size].astype(np.float32)/(size-1);v=1-v
rng=np.random.default_rng(310109);noise=rng.normal(0,1,(size,size)).astype(np.float32)
path=[(.50,.06),(.63,.33),(.43,.33),(.60,.59),(.40,.59),(.50,.94)]
d=np.full((size,size),5.,np.float32)
for (ax,ay),(bx,by) in zip(path,path[1:]):
 dx=bx-ax;dy=by-ay;t=np.clip(((u-ax)*dx+(v-ay)*dy)/(dx*dx+dy*dy),0,1)
 d=np.minimum(d,np.sqrt((u-ax-t*dx)**2+(v-ay-t*dy)**2))
groove=np.clip((.022-d)/.009,0,1);silver=np.clip((.009-d)/.003,0,1)
edge=np.clip((.07-np.minimum(u,1-u))/.035,0,1)
grain=.015*np.sin(u*900+v*37)+.006*noise
base=np.stack([.22+grain,.20+grain,.175+grain],axis=-1)
base=base*(1-.58*groove[:,:,None]);base=base*(1-silver[:,:,None])+np.array([.57,.61,.64])*silver[:,:,None]
base+=edge[:,:,None]*np.array([.10,.10,.095])
height=-.0018*groove+.000015*np.sin(u*900+v*37)+.000005*noise
dv,du=np.gradient(height,1/size,1/size);n=np.stack([-du,dv,np.ones_like(du)],axis=-1);n/=np.linalg.norm(n,axis=-1,keepdims=True)
orm=np.stack([1-.22*groove,np.clip(.37+.06*noise-.08*silver,.25,.60),np.full_like(u,.92)],axis=-1)
for key,data in [('BaseColor',base),('ORM',orm),('Normal',n*.5+.5)]:
 Image.fromarray(np.uint8(np.clip(data,0,1)*255)).save(P/('T_ThunderSeatV9_Crown_'+key+'.png'))
print('CROWN_PBR_SAVED')
# Continuous two-strand return knot. U wraps once around the closed bezel;
# interlaced silver channels stay flush with the forged annular surface.
a=.46+.12*np.sin(16*np.pi*u);b=.46-.12*np.sin(16*np.pi*u)
d=np.minimum(np.abs(v-a),np.abs(v-b));groove=np.clip((.024-d)/.012,0,1);silver=np.clip((.010-d)/.005,0,1)
grain=.008*np.sin(u*950+v*33)+.003*noise
base=np.stack([.27+grain,.255+grain,.23+grain],axis=-1)*(1-.55*groove[:,:,None])
base=base*(1-silver[:,:,None])+np.array([.62,.64,.66])*silver[:,:,None]
height=-.0015*groove+.000010*np.sin(u*950+v*33)+.000003*noise
dv,du=np.gradient(height,1/size,1/size);n=np.stack([-du,dv,np.ones_like(du)],axis=-1);n/=np.linalg.norm(n,axis=-1,keepdims=True)
orm=np.stack([1-.20*groove,np.clip(.37+.035*noise-.08*silver,.25,.55),np.full_like(u,.93)],axis=-1)
for key,data in [('BaseColor',base),('ORM',orm),('Normal',n*.5+.5)]:
 Image.fromarray(np.uint8(np.clip(data,0,1)*255)).save(P/('T_ThunderSeatV9_ReturnRing_'+key+'.png'))
print('RETURN_RING_PBR_SAVED')
