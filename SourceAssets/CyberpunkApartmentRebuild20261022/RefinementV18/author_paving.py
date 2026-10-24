"""Generate seamless physical paving data: albedo, DirectX normal and ORM."""
from pathlib import Path
import numpy as np
from PIL import Image
R=Path(__file__).resolve().parent;out=R/'Textures';out.mkdir(exist_ok=True)
n=1024;y,x=np.mgrid[:n,:n];u=x/n*4.;v=y/n*4.
row=np.floor(v/.5);col=np.floor((u+row%2*.5)/1.)
fx=np.mod(u+row%2*.5,1.);fy=np.mod(v,.5)
d=np.minimum(np.minimum(fx,1-fx),np.minimum(fy,.5-fy))
bevel=np.clip((d-.008)/.018,0,1)
rng=np.random.default_rng(18023)
grain=rng.normal(0,.0012,(n,n))
height=bevel*.006+grain*.3
dx=(np.roll(height,-1,1)-np.roll(height,1,1))/(8/n)
dy=(np.roll(height,-1,0)-np.roll(height,1,0))/(8/n)
normal=np.stack([-dx,dy,np.ones_like(dx)],axis=-1)
normal/=np.linalg.norm(normal,axis=-1,keepdims=True)
tile=(np.sin(col*17.1+row*29.7)*437.1)%1
base=(.42+.055*tile+.045*bevel+grain*8)[...,None]*np.array([.95,1.,1.01])
base*=np.where(d<.009,.60,1)[...,None]
orm=np.stack([.75+.25*bevel,.76+.09*tile,np.zeros_like(d)],axis=-1)
for suffix,data in [('BC',base),('N',normal*.5+.5),('ORM',orm)]:
 Image.fromarray((np.clip(data,0,1)*255+.5).astype('uint8')).save(out/f'T_AP18_Paving_{suffix}.png')
print('AP18_PAVING_AUTHORED',flush=True)
