"""Bake periodic cotton 2/1 twill relief into production PBR textures."""
import json
from pathlib import Path
import numpy as np
from scipy.ndimage import gaussian_filter
from PIL import Image
R=Path('D:/FPS3D/FPSGAME/SourceAssets/SmokeGreyCapri20261004');out=R/'Textures';out.mkdir(exist_ok=True)
n=1024;span=6.25;rng=np.random.default_rng(1004);y,x=np.mgrid[:n,:n]/n
# 144 yarns per tile, approximately .434 mm pitch; 2-over-1 twill crossover.
u=x*144;v=y*144;i=np.floor(u).astype(int);j=np.floor(v).astype(int)
warp=((i-j)%3<2);a=np.sin(np.pi*(u%1))**.65;b=np.sin(np.pi*(v%1))**.65
micro=gaussian_filter(rng.normal(size=(n,n)),.7,mode='wrap')
slub=gaussian_filter(rng.normal(size=(n,n)),(1,7),mode='wrap')
height=.009*np.where(warp,a,b)+.0015*micro+.001*slub
broad=gaussian_filter(rng.normal(size=(n,n)),20,mode='wrap');broad/=max(broad.std(),1e-6)
color=np.array([87.,88.,82.])[None,None,:]+(height/.009-.6)[:,:,None]*7+broad[:,:,None]*1.0
color=np.clip(color,0,255).astype(np.uint8)
step=span/n;dx=(np.roll(height,-1,axis=1)-np.roll(height,1,axis=1))/(2*step);dy=(np.roll(height,-1,axis=0)-np.roll(height,1,axis=0))/(2*step)
normal=np.stack([-dx,-dy,np.ones_like(dx)],axis=2);normal/=np.linalg.norm(normal,axis=2,keepdims=True)
normal=np.clip((normal*.5+.5)*255,0,255).astype(np.uint8)
orm=np.empty((n,n,3),np.uint8);orm[:,:,0]=np.clip(242+10*height/.009,0,255);orm[:,:,1]=np.clip(222+6*micro-5*height/.009,0,255);orm[:,:,2]=0
for channel,values in [('BaseColor',color),('Normal',normal),('ORM',orm)]:Image.fromarray(values).save(out/('T_SmokeGreyTwill_'+channel+'.png'))
np.savez_compressed(R/'TwillHighField.npz',height_cm=height.astype(np.float32),span_cm=span)
(R/'surface_bake.json').write_text(json.dumps(dict(source='authored periodic 2-over-1 cotton twill relief',resolution=n,span_cm=span,yarn_pitch_mm=span*10/144,normal_convention='OpenGL; UE import flips green',channels=['BaseColor sRGB','Normal linear','ORM linear'],runtime_tested=False),indent=2),encoding='utf-8')
print('CAPRI_COTTON_SURFACES_BAKED',flush=True)
